"""
Schema Extractor - Extract table schema metadata from databases.

Supports PostgreSQL and MSSQL databases, extracting columns, indexes,
primary keys, foreign keys, check constraints, stored procedures, views,
and triggers.
"""

import hashlib
import logging
from abc import ABC, abstractmethod
from typing import Optional

from src.core.schema_comparator import (
    TableSchema,
    ColumnSchema,
    IndexSchema,
    ForeignKeySchema,
    CheckConstraintSchema,
    StoredProcedureSchema,
    ViewSchema,
    TriggerSchema,
)
from src.config import Config

logger = logging.getLogger(__name__)


def _md5_hash(text: str) -> str:
    """Compute MD5 hash of text for definition drift detection."""
    if not text:
        return ''
    return hashlib.md5(text.encode('utf-8')).hexdigest()


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
    
    @abstractmethod
    def extract_stored_procedures(
        self,
        schema_name: Optional[str] = None
    ) -> list[StoredProcedureSchema]:
        """Extract stored procedures/functions from schema."""
        pass
    
    @abstractmethod
    def extract_views(
        self,
        schema_name: Optional[str] = None
    ) -> list[ViewSchema]:
        """Extract views from schema."""
        pass
    
    @abstractmethod
    def extract_triggers(
        self,
        schema_name: Optional[str] = None
    ) -> list[TriggerSchema]:
        """Extract triggers from schema."""
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
    
    def extract_stored_procedures(
        self,
        schema_name: Optional[str] = None
    ) -> list[StoredProcedureSchema]:
        """Extract stored procedures/functions from PostgreSQL."""
        schema_name = schema_name or Config.POSTGRES_SCHEMA or 'public'
        query = """
            SELECT
                p.proname AS name,
                l.lanname AS language,
                pg_catalog.pg_get_function_arguments(p.oid) AS parameter_list,
                pg_catalog.pg_get_function_result(p.oid) AS return_type,
                pg_catalog.pg_get_functiondef(p.oid) AS definition
            FROM pg_catalog.pg_proc p
            JOIN pg_catalog.pg_namespace n ON n.oid = p.pronamespace
            JOIN pg_catalog.pg_language l ON l.oid = p.prolang
            WHERE n.nspname = %s
              AND p.prokind IN ('f', 'p')
            ORDER BY p.proname
        """
        
        procedures = []
        cursor = self.connection.cursor()
        try:
            cursor.execute(query, (schema_name,))
            for row in cursor.fetchall():
                name, language, params, return_type, definition = row
                procedures.append(StoredProcedureSchema(
                    name=name,
                    schema_name=schema_name,
                    language=language or '',
                    parameter_list=params or '',
                    return_type=return_type or '',
                    definition_hash=_md5_hash(definition or ''),
                ))
        except Exception as e:
            logger.warning(f"Could not extract stored procedures: {e}")
        finally:
            cursor.close()
        
        logger.info(f"Extracted {len(procedures)} stored procedures from {schema_name}")
        return procedures
    
    def extract_views(
        self,
        schema_name: Optional[str] = None
    ) -> list[ViewSchema]:
        """Extract views from PostgreSQL (including materialized views)."""
        schema_name = schema_name or Config.POSTGRES_SCHEMA or 'public'
        
        views = []
        cursor = self.connection.cursor()
        try:
            # Regular views
            cursor.execute("""
                SELECT
                    v.table_name,
                    v.view_definition
                FROM information_schema.views v
                WHERE v.table_schema = %s
                ORDER BY v.table_name
            """, (schema_name,))
            for row in cursor.fetchall():
                name, definition = row
                # Get view columns
                cursor2 = self.connection.cursor()
                try:
                    cursor2.execute("""
                        SELECT column_name
                        FROM information_schema.columns
                        WHERE table_schema = %s AND table_name = %s
                        ORDER BY ordinal_position
                    """, (schema_name, name))
                    cols = ','.join(r[0] for r in cursor2.fetchall())
                finally:
                    cursor2.close()
                
                views.append(ViewSchema(
                    name=name,
                    schema_name=schema_name,
                    definition_hash=_md5_hash(definition or ''),
                    is_materialized=False,
                    columns=cols,
                ))
            
            # Materialized views
            cursor.execute("""
                SELECT
                    c.relname AS name,
                    pg_catalog.pg_get_viewdef(c.oid, true) AS definition
                FROM pg_catalog.pg_class c
                JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname = %s
                  AND c.relkind = 'm'
                ORDER BY c.relname
            """, (schema_name,))
            for row in cursor.fetchall():
                name, definition = row
                # Get materialized view columns
                cursor2 = self.connection.cursor()
                try:
                    cursor2.execute("""
                        SELECT a.attname
                        FROM pg_catalog.pg_attribute a
                        JOIN pg_catalog.pg_class c ON c.oid = a.attrelid
                        JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
                        WHERE n.nspname = %s AND c.relname = %s
                          AND a.attnum > 0 AND NOT a.attisdropped
                        ORDER BY a.attnum
                    """, (schema_name, name))
                    cols = ','.join(r[0] for r in cursor2.fetchall())
                finally:
                    cursor2.close()
                
                views.append(ViewSchema(
                    name=name,
                    schema_name=schema_name,
                    definition_hash=_md5_hash(definition or ''),
                    is_materialized=True,
                    columns=cols,
                ))
        except Exception as e:
            logger.warning(f"Could not extract views: {e}")
        finally:
            cursor.close()
        
        logger.info(f"Extracted {len(views)} views from {schema_name}")
        return views
    
    def extract_triggers(
        self,
        schema_name: Optional[str] = None
    ) -> list[TriggerSchema]:
        """Extract triggers from PostgreSQL."""
        schema_name = schema_name or Config.POSTGRES_SCHEMA or 'public'
        query = """
            SELECT
                t.trigger_name,
                t.event_object_table,
                t.event_manipulation,
                t.action_timing,
                t.action_statement
            FROM information_schema.triggers t
            WHERE t.trigger_schema = %s
            ORDER BY t.trigger_name, t.event_manipulation
        """
        
        # Aggregate multiple events for same trigger
        trigger_map = {}
        cursor = self.connection.cursor()
        try:
            cursor.execute(query, (schema_name,))
            for row in cursor.fetchall():
                name, table, event, timing, statement = row
                if name not in trigger_map:
                    trigger_map[name] = {
                        'table': table,
                        'events': [],
                        'timing': timing,
                        'statement': statement,
                    }
                trigger_map[name]['events'].append(event)
        except Exception as e:
            logger.warning(f"Could not extract triggers: {e}")
        finally:
            cursor.close()
        
        triggers = []
        for name, info in trigger_map.items():
            triggers.append(TriggerSchema(
                name=name,
                schema_name=schema_name,
                table_name=info['table'],
                event=','.join(info['events']),
                timing=info['timing'],
                definition_hash=_md5_hash(info['statement'] or ''),
            ))
        
        logger.info(f"Extracted {len(triggers)} triggers from {schema_name}")
        return triggers


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
    
    def extract_stored_procedures(
        self,
        schema_name: Optional[str] = None
    ) -> list[StoredProcedureSchema]:
        """Extract stored procedures from MSSQL."""
        schema_name = schema_name or Config.MSSQL_SCHEMA or 'dbo'
        query = """
            SELECT
                p.name,
                ISNULL(m.definition, '') AS definition
            FROM sys.procedures p
            JOIN sys.schemas s ON p.schema_id = s.schema_id
            LEFT JOIN sys.sql_modules m ON p.object_id = m.object_id
            WHERE s.name = %s
            ORDER BY p.name
        """
        
        procedures = []
        cursor = self.connection.cursor()
        try:
            cursor.execute(query, (schema_name,))
            for row in cursor.fetchall():
                name, definition = row
                procedures.append(StoredProcedureSchema(
                    name=name,
                    schema_name=schema_name,
                    language='tsql',
                    parameter_list='',
                    return_type='',
                    definition_hash=_md5_hash(definition or ''),
                ))
        except Exception as e:
            logger.warning(f"Could not extract stored procedures: {e}")
        finally:
            cursor.close()
        
        logger.info(f"Extracted {len(procedures)} stored procedures from {schema_name}")
        return procedures
    
    def extract_views(
        self,
        schema_name: Optional[str] = None
    ) -> list[ViewSchema]:
        """Extract views from MSSQL."""
        schema_name = schema_name or Config.MSSQL_SCHEMA or 'dbo'
        query = """
            SELECT
                v.name,
                ISNULL(m.definition, '') AS definition,
                STRING_AGG(c.name, ',') WITHIN GROUP (ORDER BY c.column_id) AS columns
            FROM sys.views v
            JOIN sys.schemas s ON v.schema_id = s.schema_id
            LEFT JOIN sys.sql_modules m ON v.object_id = m.object_id
            LEFT JOIN sys.columns c ON v.object_id = c.object_id
            WHERE s.name = %s
            GROUP BY v.name, m.definition
            ORDER BY v.name
        """
        
        views = []
        cursor = self.connection.cursor()
        try:
            cursor.execute(query, (schema_name,))
            for row in cursor.fetchall():
                name, definition, columns = row
                views.append(ViewSchema(
                    name=name,
                    schema_name=schema_name,
                    definition_hash=_md5_hash(definition or ''),
                    is_materialized=False,
                    columns=columns or '',
                ))
        except Exception as e:
            logger.warning(f"Could not extract views: {e}")
        finally:
            cursor.close()
        
        logger.info(f"Extracted {len(views)} views from {schema_name}")
        return views
    
    def extract_triggers(
        self,
        schema_name: Optional[str] = None
    ) -> list[TriggerSchema]:
        """Extract triggers from MSSQL."""
        schema_name = schema_name or Config.MSSQL_SCHEMA or 'dbo'
        query = """
            SELECT
                tr.name AS trigger_name,
                OBJECT_NAME(tr.parent_id) AS table_name,
                te.type_desc AS event,
                CASE WHEN tr.is_instead_of_trigger = 1 THEN 'INSTEAD OF' ELSE 'AFTER' END AS timing,
                ISNULL(m.definition, '') AS definition
            FROM sys.triggers tr
            JOIN sys.trigger_events te ON tr.object_id = te.object_id
            LEFT JOIN sys.sql_modules m ON tr.object_id = m.object_id
            JOIN sys.tables t ON tr.parent_id = t.object_id
            JOIN sys.schemas s ON t.schema_id = s.schema_id
            WHERE s.name = %s
            ORDER BY tr.name
        """
        
        trigger_map = {}
        cursor = self.connection.cursor()
        try:
            cursor.execute(query, (schema_name,))
            for row in cursor.fetchall():
                name, table, event, timing, definition = row
                if name not in trigger_map:
                    trigger_map[name] = {
                        'table': table,
                        'events': [],
                        'timing': timing,
                        'definition': definition,
                    }
                trigger_map[name]['events'].append(event)
        except Exception as e:
            logger.warning(f"Could not extract triggers: {e}")
        finally:
            cursor.close()
        
        triggers = []
        for name, info in trigger_map.items():
            triggers.append(TriggerSchema(
                name=name,
                schema_name=schema_name,
                table_name=info['table'],
                event=','.join(info['events']),
                timing=info['timing'],
                definition_hash=_md5_hash(info['definition'] or ''),
            ))
        
        logger.info(f"Extracted {len(triggers)} triggers from {schema_name}")
        return triggers


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
    
    def extract_stored_procedures(
        self,
        schema_name: Optional[str] = None
    ) -> list[StoredProcedureSchema]:
        """Extract stored procedures/functions from MySQL."""
        schema_name = schema_name or self.database or 'prod'
        query = """
            SELECT
                ROUTINE_NAME,
                ROUTINE_TYPE,
                DTD_IDENTIFIER,
                ROUTINE_BODY,
                ROUTINE_DEFINITION
            FROM information_schema.ROUTINES
            WHERE ROUTINE_SCHEMA = %s
            ORDER BY ROUTINE_NAME
        """
        
        procedures = []
        cursor = self.connection.cursor()
        try:
            cursor.execute(query, (schema_name,))
            for row in cursor.fetchall():
                name, rtype, return_type, body_lang, definition = row
                name = self._decode(name)
                return_type = self._decode(return_type) if return_type else ''
                body_lang = self._decode(body_lang) if body_lang else ''
                definition = self._decode(definition) if definition else ''
                
                procedures.append(StoredProcedureSchema(
                    name=name,
                    schema_name=schema_name,
                    language=body_lang,
                    parameter_list='',
                    return_type=return_type if rtype == 'FUNCTION' else '',
                    definition_hash=_md5_hash(definition),
                ))
        except Exception as e:
            logger.warning(f"Could not extract stored procedures: {e}")
        finally:
            cursor.close()
        
        logger.info(f"Extracted {len(procedures)} stored procedures from {schema_name}")
        return procedures
    
    def extract_views(
        self,
        schema_name: Optional[str] = None
    ) -> list[ViewSchema]:
        """Extract views from MySQL."""
        schema_name = schema_name or self.database or 'prod'
        query = """
            SELECT
                TABLE_NAME,
                VIEW_DEFINITION
            FROM information_schema.VIEWS
            WHERE TABLE_SCHEMA = %s
            ORDER BY TABLE_NAME
        """
        
        views = []
        cursor = self.connection.cursor()
        try:
            cursor.execute(query, (schema_name,))
            for row in cursor.fetchall():
                name, definition = row
                name = self._decode(name)
                definition = self._decode(definition) if definition else ''
                
                # Get columns
                cursor2 = self.connection.cursor()
                try:
                    cursor2.execute("""
                        SELECT COLUMN_NAME
                        FROM information_schema.COLUMNS
                        WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
                        ORDER BY ORDINAL_POSITION
                    """, (schema_name, name))
                    cols = ','.join(self._decode(r[0]) for r in cursor2.fetchall())
                finally:
                    cursor2.close()
                
                views.append(ViewSchema(
                    name=name,
                    schema_name=schema_name,
                    definition_hash=_md5_hash(definition),
                    is_materialized=False,
                    columns=cols,
                ))
        except Exception as e:
            logger.warning(f"Could not extract views: {e}")
        finally:
            cursor.close()
        
        logger.info(f"Extracted {len(views)} views from {schema_name}")
        return views
    
    def extract_triggers(
        self,
        schema_name: Optional[str] = None
    ) -> list[TriggerSchema]:
        """Extract triggers from MySQL."""
        schema_name = schema_name or self.database or 'prod'
        query = """
            SELECT
                TRIGGER_NAME,
                EVENT_OBJECT_TABLE,
                EVENT_MANIPULATION,
                ACTION_TIMING,
                ACTION_STATEMENT
            FROM information_schema.TRIGGERS
            WHERE TRIGGER_SCHEMA = %s
            ORDER BY TRIGGER_NAME
        """
        
        triggers = []
        cursor = self.connection.cursor()
        try:
            cursor.execute(query, (schema_name,))
            for row in cursor.fetchall():
                name, table, event, timing, statement = row
                name = self._decode(name)
                table = self._decode(table)
                event = self._decode(event)
                timing = self._decode(timing)
                statement = self._decode(statement) if statement else ''
                
                triggers.append(TriggerSchema(
                    name=name,
                    schema_name=schema_name,
                    table_name=table,
                    event=event,
                    timing=timing,
                    definition_hash=_md5_hash(statement),
                ))
        except Exception as e:
            logger.warning(f"Could not extract triggers: {e}")
        finally:
            cursor.close()
        
        logger.info(f"Extracted {len(triggers)} triggers from {schema_name}")
        return triggers



class OracleSchemaExtractor(SchemaExtractor):
    """Extract schema from Oracle databases."""
    
    def __init__(self, connection):
        """
        Initialize with an oracledb connection.
        
        Args:
            connection: Active oracledb connection
        """
        self.connection = connection
        self.host = Config.ORACLE_HOST
        # Oracle uses service name usually, but we keep the structure generic
        self.database = Config.ORACLE_SERVICE_NAME
    
    def extract_table_schema(
        self,
        table_name: str,
        schema_name: Optional[str] = None
    ) -> TableSchema:
        """Extract complete schema for an Oracle table."""
        schema_name = (schema_name or Config.ORACLE_SCHEMA or 'USER').upper()
        
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
                nullable,
                data_default,
                data_length,
                data_precision,
                data_scale
            FROM all_tab_columns
            WHERE owner = :1 AND table_name = :2
            ORDER BY column_id
        """
        
        columns = {}
        cursor = self.connection.cursor()
        try:
            cursor.execute(query, (schema_name, table_name.upper()))
            for row in cursor.fetchall():
                col_name, data_type, nullable, default, max_len, precision, scale = row
                
                # Format type
                full_type = data_type.lower()
                if max_len and data_type in ('VARCHAR2', 'CHAR', 'NVARCHAR2', 'NCHAR'):
                    full_type = f"{full_type}({max_len})"
                elif precision and data_type in ('NUMBER',):
                    full_type = f"{full_type}({precision},{scale or 0})"
                
                # Handle default value (Oracle returns it as LONG sometimes or string)
                default_val = str(default) if default is not None else None
                
                columns[col_name] = ColumnSchema(
                    name=col_name,
                    data_type=full_type,
                    is_nullable=(nullable == 'Y'),
                    default_value=default_val,
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
            SELECT ALL_CONS_COLUMNS.COLUMN_NAME
            FROM ALL_CONSTRAINTS
            JOIN ALL_CONS_COLUMNS ON ALL_CONSTRAINTS.CONSTRAINT_NAME = ALL_CONS_COLUMNS.CONSTRAINT_NAME
                AND ALL_CONSTRAINTS.OWNER = ALL_CONS_COLUMNS.OWNER
            WHERE ALL_CONSTRAINTS.CONSTRAINT_TYPE = 'P'
                AND ALL_CONSTRAINTS.OWNER = :1
                AND ALL_CONSTRAINTS.TABLE_NAME = :2
            ORDER BY ALL_CONS_COLUMNS.POSITION
        """
        
        cursor = self.connection.cursor()
        try:
            cursor.execute(query, (schema_name, table_name.upper()))
            columns = [row[0] for row in cursor.fetchall()]
            return tuple(columns) if columns else None
        finally:
            cursor.close()
    
    def _extract_indexes(
        self,
        table_name: str,
        schema_name: str
    ) -> list[IndexSchema]:
        """Extract index definitions (excluding PK)."""
        # First find PK constraint name to exclude its index
        pk_query = """
            SELECT INDEX_NAME FROM ALL_CONSTRAINTS 
            WHERE OWNER = :1 AND TABLE_NAME = :2 AND CONSTRAINT_TYPE = 'P'
        """
        
        cursor = self.connection.cursor()
        try:
            cursor.execute(pk_query, (schema_name, table_name.upper()))
            pk_idx_row = cursor.fetchone()
            pk_index = pk_idx_row[0] if pk_idx_row else None
            
            # Fetch indexes
            query = """
                SELECT 
                    ai.INDEX_NAME,
                    aic.COLUMN_NAME,
                    ai.UNIQUENESS,
                    ai.INDEX_TYPE
                FROM ALL_INDEXES ai
                JOIN ALL_IND_COLUMNS aic ON ai.INDEX_NAME = aic.INDEX_NAME AND ai.OWNER = aic.INDEX_OWNER
                WHERE ai.OWNER = :1 AND ai.TABLE_NAME = :2
                ORDER BY ai.INDEX_NAME, aic.COLUMN_POSITION
            """
            
            cursor.execute(query, (schema_name, table_name.upper()))
            
            indexes_map = {}
            for row in cursor.fetchall():
                idx_name, col_name, uniqueness, idx_type = row
                
                # Skip PK index
                if idx_name == pk_index:
                    continue
                    
                if idx_name not in indexes_map:
                    indexes_map[idx_name] = {
                        'columns': [],
                        'unique': uniqueness == 'UNIQUE',
                        'type': idx_type
                    }
                indexes_map[idx_name]['columns'].append(col_name)
            
            indexes = []
            for name, info in indexes_map.items():
                indexes.append(IndexSchema(
                    name=name,
                    columns=tuple(info['columns']),
                    is_unique=info['unique'],
                    index_type=info['type']
                ))
            return indexes
            
        finally:
            cursor.close()
    
    def _extract_foreign_keys(
        self,
        table_name: str,
        schema_name: str
    ) -> list[ForeignKeySchema]:
        """Extract foreign key definitions."""
        query = """
            SELECT 
                ac.CONSTRAINT_NAME,
                acc.COLUMN_NAME,
                r_ac.OWNER AS REF_OWNER,
                r_ac.TABLE_NAME AS REF_TABLE,
                ac.DELETE_RULE
            FROM ALL_CONSTRAINTS ac
            JOIN ALL_CONS_COLUMNS acc ON ac.CONSTRAINT_NAME = acc.CONSTRAINT_NAME 
                AND ac.OWNER = acc.OWNER
            JOIN ALL_CONSTRAINTS r_ac ON ac.R_CONSTRAINT_NAME = r_ac.CONSTRAINT_NAME 
                AND ac.R_OWNER = r_ac.OWNER
            WHERE ac.CONSTRAINT_TYPE = 'R'
                AND ac.OWNER = :1
                AND ac.TABLE_NAME = :2
            ORDER BY ac.CONSTRAINT_NAME, acc.POSITION
        """
        
        cursor = self.connection.cursor()
        try:
            cursor.execute(query, (schema_name, table_name.upper()))
            
            fk_map = {}
            for row in cursor.fetchall():
                name, col, ref_owner, ref_table, del_rule = row
                
                if name not in fk_map:
                    fk_map[name] = {
                        'columns': [],
                        'ref_table': f"{ref_owner}.{ref_table}" if ref_owner != schema_name else ref_table,
                        'del_rule': del_rule,
                        # Getting referenced columns in Oracle is tricky without joining ALL_CONS_COLUMNS for remote constraint too.
                        # For simplicity in this iteration, we might assume same order or fetch separately.
                        # Let's fetch referenced columns separately.
                    }
                fk_map[name]['columns'].append(col)
            
            # Populate referenced columns
            foreign_keys = []
            for name, info in fk_map.items():
                # Get referenced columns
                ref_query = """
                    SELECT acc.COLUMN_NAME
                    FROM ALL_CONSTRAINTS ac
                    JOIN ALL_CONSTRAINTS r_ac ON ac.R_CONSTRAINT_NAME = r_ac.CONSTRAINT_NAME
                        AND ac.R_OWNER = r_ac.OWNER
                    JOIN ALL_CONS_COLUMNS acc ON r_ac.CONSTRAINT_NAME = acc.CONSTRAINT_NAME
                        AND r_ac.OWNER = acc.OWNER
                    WHERE ac.CONSTRAINT_NAME = :1 AND ac.OWNER = :2
                    ORDER BY acc.POSITION
                """
                cursor.execute(ref_query, (name, schema_name))
                ref_cols = [r[0] for r in cursor.fetchall()]
                
                foreign_keys.append(ForeignKeySchema(
                    name=name,
                    columns=tuple(info['columns']),
                    referenced_table=info['ref_table'],
                    referenced_columns=tuple(ref_cols),
                    on_delete=info['del_rule'],
                    on_update='NO ACTION' # Oracle doesn't standardly support ON UPDATE CASCADE
                ))
                
            return foreign_keys
        finally:
            cursor.close()
    
    def _extract_check_constraints(
        self,
        table_name: str,
        schema_name: str
    ) -> list[CheckConstraintSchema]:
        """Extract check constraint definitions."""
        query = """
            SELECT CONSTRAINT_NAME, SEARCH_CONDITION_VC
            FROM ALL_CONSTRAINTS
            WHERE OWNER = :1 AND TABLE_NAME = :2 AND CONSTRAINT_TYPE = 'C'
        """
        
        constraints = []
        cursor = self.connection.cursor()
        try:
            cursor.execute(query, (schema_name, table_name.upper()))
            for row in cursor.fetchall():
                name, expression = row
                # Filter out "IS NOT NULL" checks which are standard
                if expression and "IS NOT NULL" not in str(expression):
                    constraints.append(CheckConstraintSchema(
                        name=name,
                        expression=str(expression),
                    ))
        finally:
            cursor.close()
        
        return constraints
    
    def extract_stored_procedures(
        self,
        schema_name: Optional[str] = None
    ) -> list[StoredProcedureSchema]:
        """Extract stored procedures from Oracle."""
        schema_name = (schema_name or Config.ORACLE_SCHEMA or 'USER').upper()
        # Note: Oracle source is in ALL_SOURCE
        query = """
            SELECT OBJECT_NAME, OBJECT_TYPE
            FROM ALL_OBJECTS
            WHERE OWNER = :1 AND OBJECT_TYPE IN ('PROCEDURE', 'FUNCTION')
            ORDER BY OBJECT_NAME
        """
        
        procedures = []
        cursor = self.connection.cursor()
        try:
            cursor.execute(query, (schema_name,))
            for row in cursor.fetchall():
                name, obj_type = row
                
                # Fetch definition
                src_query = """
                    SELECT TEXT FROM ALL_SOURCE 
                    WHERE OWNER = :1 AND NAME = :2 AND TYPE = :3 
                    ORDER BY LINE
                """
                cursor2 = self.connection.cursor()
                try:
                    cursor2.execute(src_query, (schema_name, name, obj_type))
                    definition = "".join([r[0] for r in cursor2.fetchall()])
                finally:
                    cursor2.close()
                
                procedures.append(StoredProcedureSchema(
                    name=name,
                    schema_name=schema_name,
                    language='plsql',
                    parameter_list='', # Parsing args in Oracle is complex
                    return_type='',
                    definition_hash=_md5_hash(definition),
                ))
        except Exception as e:
            logger.warning(f"Could not extract stored procedures: {e}")
        finally:
            cursor.close()
        
        return procedures
    
    def extract_views(
        self,
        schema_name: Optional[str] = None
    ) -> list[ViewSchema]:
        """Extract views from Oracle."""
        schema_name = (schema_name or Config.ORACLE_SCHEMA or 'USER').upper()
        query = """
            SELECT VIEW_NAME, TEXT
            FROM ALL_VIEWS
            WHERE OWNER = :1
            ORDER BY VIEW_NAME
        """
        
        views = []
        cursor = self.connection.cursor()
        try:
            cursor.execute(query, (schema_name,))
            for row in cursor.fetchall():
                name, definition = row
                definition = str(definition) if definition else ''
                
                # Get columns
                col_query = """
                    SELECT COLUMN_NAME FROM ALL_TAB_COLUMNS 
                    WHERE OWNER = :1 AND TABLE_NAME = :2 
                    ORDER BY COLUMN_ID
                """
                cursor2 = self.connection.cursor()
                try:
                    cursor2.execute(col_query, (schema_name, name))
                    cols = ','.join([r[0] for r in cursor2.fetchall()])
                finally:
                    cursor2.close()
                
                views.append(ViewSchema(
                    name=name,
                    schema_name=schema_name,
                    definition_hash=_md5_hash(definition),
                    is_materialized=False,
                    columns=cols,
                ))
        except Exception as e:
            logger.warning(f"Could not extract views: {e}")
        finally:
            cursor.close()
        
        return views
    
    def extract_triggers(
        self,
        schema_name: Optional[str] = None
    ) -> list[TriggerSchema]:
        """Extract triggers from Oracle."""
        schema_name = (schema_name or Config.ORACLE_SCHEMA or 'USER').upper()
        query = """
            SELECT 
                TRIGGER_NAME,
                TABLE_NAME,
                TRIGGERING_EVENT,
                TRIGGER_TYPE,
                TRIGGER_BODY
            FROM ALL_TRIGGERS
            WHERE OWNER = :1
            ORDER BY TRIGGER_NAME
        """
        
        triggers = []
        cursor = self.connection.cursor()
        try:
            cursor.execute(query, (schema_name,))
            for row in cursor.fetchall():
                name, table, event, timing, body = row
                body = str(body) if body else ''
                
                triggers.append(TriggerSchema(
                    name=name,
                    schema_name=schema_name,
                    table_name=table,
                    event=event,
                    timing=timing,
                    definition_hash=_md5_hash(body),
                ))
        except Exception as e:
            logger.warning(f"Could not extract triggers: {e}")
        finally:
            cursor.close()
        
        return triggers


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
    elif database_type == 'oracle':
        return OracleSchemaExtractor(connection)
    else:
        raise ValueError(f"Unsupported database type: {database_type}")
