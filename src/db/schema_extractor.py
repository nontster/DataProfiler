"""
Schema Extractor - Extract table schema metadata from databases.

Supports PostgreSQL and MSSQL databases, extracting columns, indexes,
primary keys, foreign keys, and check constraints.
"""

import logging
from abc import ABC, abstractmethod
from typing import Optional

from src.core.schema_comparator import (
    TableSchema,
    ColumnSchema,
    IndexSchema,
    ForeignKeySchema,
    CheckConstraintSchema,
)
from src.config import Config

logger = logging.getLogger(__name__)


class SchemaExtractor(ABC):
    """Abstract base class for schema extraction."""
    
    @abstractmethod
    def extract_table_schema(
        self,
        table_name: str,
        schema_name: Optional[str] = None
    ) -> TableSchema:
        """Extract complete schema for a table."""
        pass


class PostgresSchemaExtractor(SchemaExtractor):
    """Extract schema from PostgreSQL databases."""
    
    def __init__(self, connection):
        """
        Initialize with a psycopg2 connection.
        
        Args:
            connection: Active psycopg2 connection
        """
        self.connection = connection
        self.host = Config.POSTGRES_HOST
        self.database = Config.POSTGRES_DATABASE
    
    def extract_table_schema(
        self,
        table_name: str,
        schema_name: Optional[str] = None
    ) -> TableSchema:
        """Extract complete schema for a PostgreSQL table."""
        schema_name = schema_name or Config.POSTGRES_SCHEMA or 'public'
        
        schema = TableSchema(
            table_name=table_name,
            database_host=self.host,
            database_name=self.database,
            schema_name=schema_name,
        )
        
        schema.columns = self._extract_columns(table_name, schema_name)
        schema.primary_key = self._extract_primary_key(table_name, schema_name)
        schema.indexes = self._extract_indexes(table_name, schema_name)
        schema.foreign_keys = self._extract_foreign_keys(table_name, schema_name)
        schema.check_constraints = self._extract_check_constraints(table_name, schema_name)
        
        logger.info(f"Extracted schema for {schema_name}.{table_name}: "
                   f"{len(schema.columns)} columns, {len(schema.indexes)} indexes, "
                   f"{len(schema.foreign_keys)} FKs")
        
        return schema
    
    def _extract_columns(
        self,
        table_name: str,
        schema_name: str
    ) -> dict[str, ColumnSchema]:
        """Extract column definitions."""
        query = """
            SELECT 
                column_name,
                data_type,
                is_nullable,
                column_default,
                character_maximum_length,
                numeric_precision,
                numeric_scale,
                udt_name
            FROM information_schema.columns
            WHERE table_schema = %s AND table_name = %s
            ORDER BY ordinal_position
        """
        
        columns = {}
        cursor = self.connection.cursor()
        try:
            cursor.execute(query, (schema_name, table_name))
            for row in cursor.fetchall():
                col_name, data_type, nullable, default, max_len, precision, scale, udt_name = row
                
                # Use udt_name for better type representation
                full_type = udt_name if udt_name else data_type
                if max_len:
                    full_type = f"{full_type}({max_len})"
                elif precision and data_type in ('numeric', 'decimal'):
                    full_type = f"{full_type}({precision},{scale or 0})"
                
                columns[col_name] = ColumnSchema(
                    name=col_name,
                    data_type=full_type,
                    is_nullable=(nullable == 'YES'),
                    default_value=default,
                    max_length=max_len,
                    numeric_precision=precision,
                    numeric_scale=scale,
                )
        finally:
            cursor.close()
        
        return columns
    
    def _extract_primary_key(
        self,
        table_name: str,
        schema_name: str
    ) -> Optional[tuple[str, ...]]:
        """Extract primary key columns."""
        query = """
            SELECT kcu.column_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
            WHERE tc.constraint_type = 'PRIMARY KEY'
                AND tc.table_schema = %s
                AND tc.table_name = %s
            ORDER BY kcu.ordinal_position
        """
        
        cursor = self.connection.cursor()
        try:
            cursor.execute(query, (schema_name, table_name))
            columns = [row[0] for row in cursor.fetchall()]
            return tuple(columns) if columns else None
        finally:
            cursor.close()
    
    def _extract_indexes(
        self,
        table_name: str,
        schema_name: str
    ) -> list[IndexSchema]:
        """Extract index definitions (excluding primary key index)."""
        query = """
            SELECT 
                i.relname as index_name,
                array_agg(a.attname ORDER BY array_position(ix.indkey, a.attnum)) as columns,
                ix.indisunique as is_unique,
                am.amname as index_type
            FROM pg_class t
            JOIN pg_index ix ON t.oid = ix.indrelid
            JOIN pg_class i ON i.oid = ix.indexrelid
            JOIN pg_namespace n ON n.oid = t.relnamespace
            JOIN pg_am am ON am.oid = i.relam
            JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = ANY(ix.indkey)
            WHERE n.nspname = %s
                AND t.relname = %s
                AND NOT ix.indisprimary  -- Exclude PK index
            GROUP BY i.relname, ix.indisunique, am.amname
            ORDER BY i.relname
        """
        
        indexes = []
        cursor = self.connection.cursor()
        try:
            cursor.execute(query, (schema_name, table_name))
            for row in cursor.fetchall():
                idx_name, columns, is_unique, idx_type = row
                indexes.append(IndexSchema(
                    name=idx_name,
                    columns=tuple(columns),
                    is_unique=is_unique,
                    index_type=idx_type or 'btree',
                ))
        finally:
            cursor.close()
        
        return indexes
    
    def _extract_foreign_keys(
        self,
        table_name: str,
        schema_name: str
    ) -> list[ForeignKeySchema]:
        """Extract foreign key definitions."""
        query = """
            SELECT
                tc.constraint_name,
                array_agg(kcu.column_name ORDER BY kcu.ordinal_position) as columns,
                ccu.table_name as referenced_table,
                array_agg(ccu.column_name ORDER BY kcu.ordinal_position) as referenced_columns,
                rc.delete_rule,
                rc.update_rule
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage ccu
                ON ccu.constraint_name = tc.constraint_name
                AND ccu.table_schema = tc.table_schema
            JOIN information_schema.referential_constraints rc
                ON rc.constraint_name = tc.constraint_name
                AND rc.constraint_schema = tc.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY'
                AND tc.table_schema = %s
                AND tc.table_name = %s
            GROUP BY tc.constraint_name, ccu.table_name, rc.delete_rule, rc.update_rule
        """
        
        foreign_keys = []
        cursor = self.connection.cursor()
        try:
            cursor.execute(query, (schema_name, table_name))
            for row in cursor.fetchall():
                fk_name, columns, ref_table, ref_columns, on_delete, on_update = row
                foreign_keys.append(ForeignKeySchema(
                    name=fk_name,
                    columns=tuple(columns),
                    referenced_table=ref_table,
                    referenced_columns=tuple(ref_columns),
                    on_delete=on_delete or 'NO ACTION',
                    on_update=on_update or 'NO ACTION',
                ))
        finally:
            cursor.close()
        
        return foreign_keys
    
    def _extract_check_constraints(
        self,
        table_name: str,
        schema_name: str
    ) -> list[CheckConstraintSchema]:
        """Extract check constraint definitions."""
        query = """
            SELECT
                cc.constraint_name,
                cc.check_clause
            FROM information_schema.check_constraints cc
            JOIN information_schema.table_constraints tc
                ON cc.constraint_name = tc.constraint_name
                AND cc.constraint_schema = tc.table_schema
            WHERE tc.table_schema = %s
                AND tc.table_name = %s
                AND tc.constraint_type = 'CHECK'
        """
        
        constraints = []
        cursor = self.connection.cursor()
        try:
            cursor.execute(query, (schema_name, table_name))
            for row in cursor.fetchall():
                name, expression = row
                # Skip system-generated NOT NULL constraints
                if expression and 'IS NOT NULL' not in expression.upper():
                    constraints.append(CheckConstraintSchema(
                        name=name,
                        expression=expression,
                    ))
        finally:
            cursor.close()
        
        return constraints


class MSSQLSchemaExtractor(SchemaExtractor):
    """Extract schema from MSSQL databases."""
    
    def __init__(self, connection):
        """
        Initialize with a pymssql connection.
        
        Args:
            connection: Active pymssql connection
        """
        self.connection = connection
        self.host = Config.MSSQL_HOST
        self.database = Config.MSSQL_DATABASE
    
    def extract_table_schema(
        self,
        table_name: str,
        schema_name: Optional[str] = None
    ) -> TableSchema:
        """Extract complete schema for an MSSQL table."""
        schema_name = schema_name or Config.MSSQL_SCHEMA or 'dbo'
        
        schema = TableSchema(
            table_name=table_name,
            database_host=self.host,
            database_name=self.database,
            schema_name=schema_name,
        )
        
        schema.columns = self._extract_columns(table_name, schema_name)
        schema.primary_key = self._extract_primary_key(table_name, schema_name)
        schema.indexes = self._extract_indexes(table_name, schema_name)
        schema.foreign_keys = self._extract_foreign_keys(table_name, schema_name)
        schema.check_constraints = self._extract_check_constraints(table_name, schema_name)
        
        logger.info(f"Extracted schema for {schema_name}.{table_name}: "
                   f"{len(schema.columns)} columns, {len(schema.indexes)} indexes, "
                   f"{len(schema.foreign_keys)} FKs")
        
        return schema
    
    def _extract_columns(
        self,
        table_name: str,
        schema_name: str
    ) -> dict[str, ColumnSchema]:
        """Extract column definitions."""
        query = """
            SELECT 
                c.COLUMN_NAME,
                c.DATA_TYPE,
                c.IS_NULLABLE,
                c.COLUMN_DEFAULT,
                c.CHARACTER_MAXIMUM_LENGTH,
                c.NUMERIC_PRECISION,
                c.NUMERIC_SCALE
            FROM INFORMATION_SCHEMA.COLUMNS c
            WHERE c.TABLE_SCHEMA = %s AND c.TABLE_NAME = %s
            ORDER BY c.ORDINAL_POSITION
        """
        
        columns = {}
        cursor = self.connection.cursor()
        try:
            cursor.execute(query, (schema_name, table_name))
            for row in cursor.fetchall():
                col_name, data_type, nullable, default, max_len, precision, scale = row
                
                # Build full type string
                full_type = data_type
                if max_len and max_len > 0:
                    if max_len == -1:
                        full_type = f"{data_type}(max)"
                    else:
                        full_type = f"{data_type}({max_len})"
                elif precision and data_type in ('numeric', 'decimal'):
                    full_type = f"{data_type}({precision},{scale or 0})"
                
                columns[col_name] = ColumnSchema(
                    name=col_name,
                    data_type=full_type,
                    is_nullable=(nullable == 'YES'),
                    default_value=default,
                    max_length=max_len if max_len and max_len > 0 else None,
                    numeric_precision=precision,
                    numeric_scale=scale,
                )
        finally:
            cursor.close()
        
        return columns
    
    def _extract_primary_key(
        self,
        table_name: str,
        schema_name: str
    ) -> Optional[tuple[str, ...]]:
        """Extract primary key columns."""
        query = """
            SELECT kcu.COLUMN_NAME
            FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc
            JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu
                ON tc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME
                AND tc.TABLE_SCHEMA = kcu.TABLE_SCHEMA
            WHERE tc.CONSTRAINT_TYPE = 'PRIMARY KEY'
                AND tc.TABLE_SCHEMA = %s
                AND tc.TABLE_NAME = %s
            ORDER BY kcu.ORDINAL_POSITION
        """
        
        cursor = self.connection.cursor()
        try:
            cursor.execute(query, (schema_name, table_name))
            columns = [row[0] for row in cursor.fetchall()]
            return tuple(columns) if columns else None
        finally:
            cursor.close()
    
    def _extract_indexes(
        self,
        table_name: str,
        schema_name: str
    ) -> list[IndexSchema]:
        """Extract index definitions (excluding primary key)."""
        query = """
            SELECT 
                i.name as index_name,
                STRING_AGG(c.name, ',') WITHIN GROUP (ORDER BY ic.key_ordinal) as columns,
                i.is_unique,
                i.type_desc as index_type
            FROM sys.indexes i
            JOIN sys.index_columns ic ON i.object_id = ic.object_id AND i.index_id = ic.index_id
            JOIN sys.columns c ON ic.object_id = c.object_id AND ic.column_id = c.column_id
            JOIN sys.tables t ON i.object_id = t.object_id
            JOIN sys.schemas s ON t.schema_id = s.schema_id
            WHERE s.name = %s
                AND t.name = %s
                AND i.is_primary_key = 0
                AND i.type > 0  -- Exclude heaps
            GROUP BY i.name, i.is_unique, i.type_desc
        """
        
        indexes = []
        cursor = self.connection.cursor()
        try:
            cursor.execute(query, (schema_name, table_name))
            for row in cursor.fetchall():
                idx_name, columns_str, is_unique, idx_type = row
                columns = tuple(columns_str.split(',')) if columns_str else ()
                indexes.append(IndexSchema(
                    name=idx_name,
                    columns=columns,
                    is_unique=bool(is_unique),
                    index_type=idx_type or 'NONCLUSTERED',
                ))
        finally:
            cursor.close()
        
        return indexes
    
    def _extract_foreign_keys(
        self,
        table_name: str,
        schema_name: str
    ) -> list[ForeignKeySchema]:
        """Extract foreign key definitions."""
        query = """
            SELECT 
                fk.name as fk_name,
                STRING_AGG(c.name, ',') WITHIN GROUP (ORDER BY fkc.constraint_column_id) as columns,
                OBJECT_NAME(fk.referenced_object_id) as referenced_table,
                STRING_AGG(rc.name, ',') WITHIN GROUP (ORDER BY fkc.constraint_column_id) as referenced_columns,
                fk.delete_referential_action_desc,
                fk.update_referential_action_desc
            FROM sys.foreign_keys fk
            JOIN sys.foreign_key_columns fkc ON fk.object_id = fkc.constraint_object_id
            JOIN sys.columns c ON fkc.parent_object_id = c.object_id AND fkc.parent_column_id = c.column_id
            JOIN sys.columns rc ON fkc.referenced_object_id = rc.object_id AND fkc.referenced_column_id = rc.column_id
            JOIN sys.tables t ON fk.parent_object_id = t.object_id
            JOIN sys.schemas s ON t.schema_id = s.schema_id
            WHERE s.name = %s AND t.name = %s
            GROUP BY fk.name, fk.referenced_object_id, 
                     fk.delete_referential_action_desc, fk.update_referential_action_desc
        """
        
        foreign_keys = []
        cursor = self.connection.cursor()
        try:
            cursor.execute(query, (schema_name, table_name))
            for row in cursor.fetchall():
                fk_name, columns_str, ref_table, ref_columns_str, on_delete, on_update = row
                columns = tuple(columns_str.split(',')) if columns_str else ()
                ref_columns = tuple(ref_columns_str.split(',')) if ref_columns_str else ()
                
                foreign_keys.append(ForeignKeySchema(
                    name=fk_name,
                    columns=columns,
                    referenced_table=ref_table,
                    referenced_columns=ref_columns,
                    on_delete=on_delete.replace('_', ' ') if on_delete else 'NO ACTION',
                    on_update=on_update.replace('_', ' ') if on_update else 'NO ACTION',
                ))
        finally:
            cursor.close()
        
        return foreign_keys
    
    def _extract_check_constraints(
        self,
        table_name: str,
        schema_name: str
    ) -> list[CheckConstraintSchema]:
        """Extract check constraint definitions."""
        query = """
            SELECT 
                cc.name as constraint_name,
                cc.definition as check_clause
            FROM sys.check_constraints cc
            JOIN sys.tables t ON cc.parent_object_id = t.object_id
            JOIN sys.schemas s ON t.schema_id = s.schema_id
            WHERE s.name = %s AND t.name = %s
        """
        
        constraints = []
        cursor = self.connection.cursor()
        try:
            cursor.execute(query, (schema_name, table_name))
            for row in cursor.fetchall():
                name, expression = row
                if expression:
                    constraints.append(CheckConstraintSchema(
                        name=name,
                        expression=expression,
                    ))
        finally:
            cursor.close()
        
        return constraints


class MySQLSchemaExtractor(SchemaExtractor):
    """Extract schema from MySQL databases."""
    
    def __init__(self, connection):
        """
        Initialize with a mysql-connector connection.
        
        Args:
            connection: Active mysql-connector connection
        """
        self.connection = connection
        self.host = Config.MYSQL_HOST
        self.database = Config.MYSQL_DATABASE
    
    def _decode(self, val):
        """Decode bytes to string if needed."""
        if isinstance(val, bytes):
            return val.decode('utf-8')
        return val
    
    def extract_table_schema(
        self,
        table_name: str,
        schema_name: Optional[str] = None
    ) -> TableSchema:
        """Extract complete schema for a MySQL table."""
        # In MySQL, schema is synonymous with database
        schema_name = schema_name or self.database or 'prod'
        
        schema = TableSchema(
            table_name=table_name,
            database_host=self.host,
            database_name=schema_name, # In MySQL, database name is the schema
            schema_name=schema_name,
        )
        
        schema.columns = self._extract_columns(table_name, schema_name)
        schema.primary_key = self._extract_primary_key(table_name, schema_name)
        schema.indexes = self._extract_indexes(table_name, schema_name)
        schema.foreign_keys = self._extract_foreign_keys(table_name, schema_name)
        schema.check_constraints = self._extract_check_constraints(table_name, schema_name)
        
        logger.info(f"Extracted schema for {schema_name}.{table_name}: "
                   f"{len(schema.columns)} columns, {len(schema.indexes)} indexes, "
                   f"{len(schema.foreign_keys)} FKs")
        
        return schema
    
    def _extract_columns(
        self,
        table_name: str,
        schema_name: str
    ) -> dict[str, ColumnSchema]:
        """Extract column definitions."""
        query = """
            SELECT 
                COLUMN_NAME,
                DATA_TYPE,
                IS_NULLABLE,
                COLUMN_DEFAULT,
                CHARACTER_MAXIMUM_LENGTH,
                NUMERIC_PRECISION,
                NUMERIC_SCALE,
                COLUMN_TYPE
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
            ORDER BY ORDINAL_POSITION
        """
        
        columns = {}
        cursor = self.connection.cursor()
        try:
            cursor.execute(query, (schema_name, table_name))
            for row in cursor.fetchall():
                col_name, data_type, nullable, default, max_len, precision, scale, col_type = row
                
                col_name = self._decode(col_name)
                data_type = self._decode(data_type)
                default = self._decode(default)
                col_type = self._decode(col_type)
                
                # COLUMN_TYPE often contains "varchar(100)" or "enum(...)" which is more descriptive
                full_type = col_type if col_type else data_type
                
                columns[col_name] = ColumnSchema(
                    name=col_name,
                    data_type=full_type,
                    is_nullable=(nullable == 'YES'),
                    default_value=str(default) if default is not None else None,
                    max_length=max_len,
                    numeric_precision=precision,
                    numeric_scale=scale,
                )
        finally:
            cursor.close()
        
        return columns
    
    def _extract_primary_key(
        self,
        table_name: str,
        schema_name: str
    ) -> Optional[tuple[str, ...]]:
        """Extract primary key columns."""
        query = """
            SELECT kcu.COLUMN_NAME
            FROM information_schema.TABLE_CONSTRAINTS tc
            JOIN information_schema.KEY_COLUMN_USAGE kcu
                ON tc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME
                AND tc.TABLE_SCHEMA = kcu.TABLE_SCHEMA
            WHERE tc.CONSTRAINT_TYPE = 'PRIMARY KEY'
                AND tc.TABLE_SCHEMA = %s
                AND tc.TABLE_NAME = %s
            ORDER BY kcu.ORDINAL_POSITION
        """
        
        cursor = self.connection.cursor()
        try:
            cursor.execute(query, (schema_name, table_name))
            columns = [self._decode(row[0]) for row in cursor.fetchall()]
            return tuple(columns) if columns else None
        finally:
            cursor.close()
    
    def _extract_indexes(
        self,
        table_name: str,
        schema_name: str
    ) -> list[IndexSchema]:
        """Extract index definitions (excluding primary key)."""
        # MySQL information_schema.STATISTICS provides index info
        query = """
            SELECT 
                INDEX_NAME,
                COLUMN_NAME,
                NON_UNIQUE,
                INDEX_TYPE
            FROM information_schema.STATISTICS
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
            AND INDEX_NAME != 'PRIMARY'
            ORDER BY INDEX_NAME, SEQ_IN_INDEX
        """
        
        indexes_dict = {}
        cursor = self.connection.cursor()
        try:
            cursor.execute(query, (schema_name, table_name))
            for row in cursor.fetchall():
                idx_name, col_name, non_unique, idx_type = row
                
                idx_name = self._decode(idx_name)
                col_name = self._decode(col_name)
                idx_type = self._decode(idx_type)
                
                if idx_name not in indexes_dict:
                    indexes_dict[idx_name] = {
                        'name': idx_name,
                        'columns': [],
                        'is_unique': not non_unique,
                        'type': idx_type
                    }
                indexes_dict[idx_name]['columns'].append(col_name)
        finally:
            cursor.close()
        
        indexes = []
        for name, info in indexes_dict.items():
            indexes.append(IndexSchema(
                name=name,
                columns=tuple(info['columns']),
                is_unique=info['is_unique'],
                index_type=info['type']
            ))
            
        return indexes
    
    def _extract_foreign_keys(
        self,
        table_name: str,
        schema_name: str
    ) -> list[ForeignKeySchema]:
        """Extract foreign key definitions."""
        query = """
            SELECT 
                kcu.CONSTRAINT_NAME,
                kcu.COLUMN_NAME,
                kcu.REFERENCED_TABLE_NAME,
                kcu.REFERENCED_COLUMN_NAME,
                rc.DELETE_RULE,
                rc.UPDATE_RULE
            FROM information_schema.KEY_COLUMN_USAGE kcu
            JOIN information_schema.REFERENTIAL_CONSTRAINTS rc
                ON kcu.CONSTRAINT_NAME = rc.CONSTRAINT_NAME
                AND kcu.CONSTRAINT_SCHEMA = rc.CONSTRAINT_SCHEMA
            WHERE kcu.TABLE_SCHEMA = %s AND kcu.TABLE_NAME = %s
            AND kcu.REFERENCED_TABLE_NAME IS NOT NULL
            ORDER BY kcu.CONSTRAINT_NAME, kcu.ORDINAL_POSITION
        """
        
        fks_dict = {}
        cursor = self.connection.cursor()
        try:
            cursor.execute(query, (schema_name, table_name))
            for row in cursor.fetchall():
                fk_name, col_name, ref_table, ref_col, on_delete, on_update = row
                
                fk_name = self._decode(fk_name)
                col_name = self._decode(col_name)
                ref_table = self._decode(ref_table)
                ref_col = self._decode(ref_col)
                on_delete = self._decode(on_delete)
                on_update = self._decode(on_update)
                
                if fk_name not in fks_dict:
                    fks_dict[fk_name] = {
                        'name': fk_name,
                        'columns': [],
                        'referenced_table': ref_table,
                        'referenced_columns': [],
                        'on_delete': on_delete,
                        'on_update': on_update
                    }
                fks_dict[fk_name]['columns'].append(col_name)
                fks_dict[fk_name]['referenced_columns'].append(ref_col)
        finally:
            cursor.close()
        
        foreign_keys = []
        for name, info in fks_dict.items():
            foreign_keys.append(ForeignKeySchema(
                name=name,
                columns=tuple(info['columns']),
                referenced_table=info['referenced_table'],
                referenced_columns=tuple(info['referenced_columns']),
                on_delete=info['on_delete'],
                on_update=info['on_update']
            ))
            
        return foreign_keys
    
    def _extract_check_constraints(
        self,
        table_name: str,
        schema_name: str
    ) -> list[CheckConstraintSchema]:
        """Extract check constraint definitions."""
        try:
            # CHECK_CONSTRAINTS table exists in MySQL 8.0.16+
            query = """
                SELECT 
                    cc.CONSTRAINT_NAME,
                    cc.CHECK_CLAUSE
                FROM information_schema.CHECK_CONSTRAINTS cc
                JOIN information_schema.TABLE_CONSTRAINTS tc
                    ON cc.CONSTRAINT_NAME = tc.CONSTRAINT_NAME
                    AND cc.CONSTRAINT_SCHEMA = tc.CONSTRAINT_SCHEMA
                WHERE tc.TABLE_SCHEMA = %s 
                  AND tc.TABLE_NAME = %s
                  AND tc.CONSTRAINT_TYPE = 'CHECK'
            """
            
            constraints = []
            cursor = self.connection.cursor()
            try:
                cursor.execute(query, (schema_name, table_name))
                for row in cursor.fetchall():
                    name, expression = row
                    name = self._decode(name)
                    expression = self._decode(expression)
                    constraints.append(CheckConstraintSchema(
                        name=name,
                        expression=expression,
                    ))
            finally:
                cursor.close()
            return constraints
        except Exception:
            # Fallback for older MySQL versions or permissions issues
            return []


def get_schema_extractor(database_type: str, connection) -> SchemaExtractor:
    """
    Factory function to get appropriate schema extractor.
    
    Args:
        database_type: 'postgresql', 'mssql', or 'mysql'
        connection: Database connection object
        
    Returns:
        SchemaExtractor instance
    """
    if database_type == 'postgresql':
        return PostgresSchemaExtractor(connection)
    elif database_type == 'mssql':
        return MSSQLSchemaExtractor(connection)
    elif database_type == 'mysql':
        return MySQLSchemaExtractor(connection)
    else:
        raise ValueError(f"Unsupported database type: {database_type}")
