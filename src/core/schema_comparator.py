"""
Schema Comparator - Semantic schema comparison for database tables.

Compares table schemas between two databases semantically, ignoring
naming differences in indexes and constraints while detecting
structural differences.
"""

from dataclasses import dataclass, field
from typing import Optional
import json


@dataclass
class ColumnSchema:
    """Represents a database column schema."""
    name: str
    data_type: str
    is_nullable: bool
    default_value: Optional[str] = None
    max_length: Optional[int] = None
    numeric_precision: Optional[int] = None
    numeric_scale: Optional[int] = None
    
    def to_dict(self) -> dict:
        return {
            'name': self.name,
            'data_type': self.data_type,
            'is_nullable': self.is_nullable,
            'default_value': self.default_value,
            'max_length': self.max_length,
            'numeric_precision': self.numeric_precision,
            'numeric_scale': self.numeric_scale,
        }
    
    def matches(self, other: 'ColumnSchema', strict: bool = True) -> tuple[bool, list[str]]:
        """Compare with another column schema."""
        differences = []
        
        if self.data_type.upper() != other.data_type.upper():
            differences.append(f"data_type: {self.data_type} vs {other.data_type}")
        
        if self.is_nullable != other.is_nullable:
            differences.append(f"nullable: {self.is_nullable} vs {other.is_nullable}")
        
        if self.max_length != other.max_length:
            differences.append(f"max_length: {self.max_length} vs {other.max_length}")
            
        if self.numeric_precision != other.numeric_precision:
            differences.append(f"precision: {self.numeric_precision} vs {other.numeric_precision}")
            
        if self.numeric_scale != other.numeric_scale:
            differences.append(f"scale: {self.numeric_scale} vs {other.numeric_scale}")
        
        if strict and self.default_value != other.default_value:
            differences.append(f"default: {self.default_value} vs {other.default_value}")
        
        return len(differences) == 0, differences


@dataclass
class IndexSchema:
    """Represents a database index schema (ignores name for comparison)."""
    name: str  # For display purposes only
    columns: tuple[str, ...]  # Tuple for hashability
    is_unique: bool
    index_type: str = "btree"  # btree, hash, gin, gist, etc.
    
    def to_dict(self) -> dict:
        return {
            'name': self.name,
            'columns': list(self.columns),
            'is_unique': self.is_unique,
            'index_type': self.index_type,
        }
    
    def signature(self) -> tuple:
        """Returns a signature for semantic comparison (ignores name)."""
        return (self.columns, self.is_unique, self.index_type.lower())
    
    def matches_semantically(self, other: 'IndexSchema') -> bool:
        """Check if indexes are semantically equivalent (ignoring name)."""
        return self.signature() == other.signature()


@dataclass
class ForeignKeySchema:
    """Represents a foreign key constraint (ignores name for comparison)."""
    name: str  # For display purposes only
    columns: tuple[str, ...]
    referenced_table: str
    referenced_columns: tuple[str, ...]
    on_delete: str = "NO ACTION"
    on_update: str = "NO ACTION"
    
    def to_dict(self) -> dict:
        return {
            'name': self.name,
            'columns': list(self.columns),
            'referenced_table': self.referenced_table,
            'referenced_columns': list(self.referenced_columns),
            'on_delete': self.on_delete,
            'on_update': self.on_update,
        }
    
    def signature(self) -> tuple:
        """Returns a signature for semantic comparison (ignores name)."""
        return (
            self.columns,
            self.referenced_table.lower(),
            self.referenced_columns,
            self.on_delete.upper(),
            self.on_update.upper(),
        )
    
    def matches_semantically(self, other: 'ForeignKeySchema') -> bool:
        """Check if FKs are semantically equivalent (ignoring name)."""
        return self.signature() == other.signature()


@dataclass
class CheckConstraintSchema:
    """Represents a check constraint (ignores name for comparison)."""
    name: str  # For display purposes only
    expression: str  # Normalized expression
    
    def to_dict(self) -> dict:
        return {
            'name': self.name,
            'expression': self.expression,
        }
    
    def normalized_expression(self) -> str:
        """Return normalized expression for comparison."""
        # Remove extra whitespace and normalize case for comparison
        return ' '.join(self.expression.split()).upper()
    
    def matches_semantically(self, other: 'CheckConstraintSchema') -> bool:
        return self.normalized_expression() == other.normalized_expression()


@dataclass
class StoredProcedureSchema:
    """Represents a stored procedure/function in the database."""
    name: str
    schema_name: str
    language: str = ""
    parameter_list: str = ""
    return_type: str = ""
    definition_hash: str = ""
    
    def to_dict(self) -> dict:
        return {
            'name': self.name,
            'schema_name': self.schema_name,
            'language': self.language,
            'parameter_list': self.parameter_list,
            'return_type': self.return_type,
            'definition_hash': self.definition_hash,
        }


@dataclass
class ViewSchema:
    """Represents a database view."""
    name: str
    schema_name: str
    definition_hash: str = ""
    is_materialized: bool = False
    columns: str = ""
    
    def to_dict(self) -> dict:
        return {
            'name': self.name,
            'schema_name': self.schema_name,
            'definition_hash': self.definition_hash,
            'is_materialized': self.is_materialized,
            'columns': self.columns,
        }


@dataclass
class TriggerSchema:
    """Represents a database trigger."""
    name: str
    schema_name: str
    table_name: str
    event: str = ""
    timing: str = ""
    definition_hash: str = ""
    
    def to_dict(self) -> dict:
        return {
            'name': self.name,
            'schema_name': self.schema_name,
            'table_name': self.table_name,
            'event': self.event,
            'timing': self.timing,
            'definition_hash': self.definition_hash,
        }


@dataclass
class TableSchema:
    """Complete table schema for comparison."""
    table_name: str
    database_host: str
    database_name: str
    schema_name: str
    columns: dict[str, ColumnSchema] = field(default_factory=dict)
    primary_key: Optional[tuple[str, ...]] = None
    indexes: list[IndexSchema] = field(default_factory=list)
    foreign_keys: list[ForeignKeySchema] = field(default_factory=list)
    check_constraints: list[CheckConstraintSchema] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            'table_name': self.table_name,
            'database_host': self.database_host,
            'database_name': self.database_name,
            'schema_name': self.schema_name,
            'columns': {k: v.to_dict() for k, v in self.columns.items()},
            'primary_key': list(self.primary_key) if self.primary_key else None,
            'indexes': [idx.to_dict() for idx in self.indexes],
            'foreign_keys': [fk.to_dict() for fk in self.foreign_keys],
            'check_constraints': [cc.to_dict() for cc in self.check_constraints],
        }


@dataclass
class ColumnDifference:
    """Represents a difference in column schema."""
    column_name: str
    difference_type: str  # 'missing_in_source', 'missing_in_target', 'mismatch'
    source_value: Optional[str] = None
    target_value: Optional[str] = None
    details: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            'column_name': self.column_name,
            'difference_type': self.difference_type,
            'source_value': self.source_value,
            'target_value': self.target_value,
            'details': self.details,
        }


@dataclass
class IndexDifference:
    """Represents a difference in index schema."""
    difference_type: str  # 'missing_in_source', 'missing_in_target'
    index_columns: tuple[str, ...]
    is_unique: bool
    index_type: str
    source_name: Optional[str] = None
    target_name: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            'difference_type': self.difference_type,
            'index_columns': list(self.index_columns),
            'is_unique': self.is_unique,
            'index_type': self.index_type,
            'source_name': self.source_name,
            'target_name': self.target_name,
        }


@dataclass
class ForeignKeyDifference:
    """Represents a difference in foreign key schema."""
    difference_type: str  # 'missing_in_source', 'missing_in_target'
    columns: tuple[str, ...]
    referenced_table: str
    referenced_columns: tuple[str, ...]
    source_name: Optional[str] = None
    target_name: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            'difference_type': self.difference_type,
            'columns': list(self.columns),
            'referenced_table': self.referenced_table,
            'referenced_columns': list(self.referenced_columns),
            'source_name': self.source_name,
            'target_name': self.target_name,
        }


@dataclass
class SchemaComparisonResult:
    """Result of comparing two table schemas."""
    table_name: str
    source_env: str
    target_env: str
    source_host: str
    target_host: str
    
    # Overall status
    is_match: bool = True
    total_differences: int = 0
    
    # Column comparison
    columns_match: bool = True
    column_differences: list[ColumnDifference] = field(default_factory=list)
    
    # Primary key comparison
    pk_match: bool = True
    source_pk: Optional[tuple[str, ...]] = None
    target_pk: Optional[tuple[str, ...]] = None
    
    # Index comparison (semantic)
    indexes_match: bool = True
    index_differences: list[IndexDifference] = field(default_factory=list)
    
    # Foreign key comparison (semantic)
    fks_match: bool = True
    fk_differences: list[ForeignKeyDifference] = field(default_factory=list)
    
    # Check constraints comparison
    checks_match: bool = True
    check_differences: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            'table_name': self.table_name,
            'source_env': self.source_env,
            'target_env': self.target_env,
            'source_host': self.source_host,
            'target_host': self.target_host,
            'is_match': self.is_match,
            'total_differences': self.total_differences,
            'columns_match': self.columns_match,
            'column_differences': [d.to_dict() for d in self.column_differences],
            'pk_match': self.pk_match,
            'source_pk': list(self.source_pk) if self.source_pk else None,
            'target_pk': list(self.target_pk) if self.target_pk else None,
            'indexes_match': self.indexes_match,
            'index_differences': [d.to_dict() for d in self.index_differences],
            'fks_match': self.fks_match,
            'fk_differences': [d.to_dict() for d in self.fk_differences],
            'checks_match': self.checks_match,
            'check_differences': self.check_differences,
        }
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


class SchemaComparator:
    """
    Compares two table schemas semantically.
    
    Ignores naming differences in indexes, constraints while
    detecting structural differences in columns, keys, etc.
    """
    
    def __init__(self, strict: bool = True):
        """
        Initialize comparator.
        
        Args:
            strict: If True, compare default values and constraint expressions
        """
        self.strict = strict
    
    def compare(
        self,
        source: TableSchema,
        target: TableSchema,
        source_env: str = "source",
        target_env: str = "target"
    ) -> SchemaComparisonResult:
        """
        Compare two table schemas.
        
        Args:
            source: Source table schema
            target: Target table schema
            source_env: Source environment name
            target_env: Target environment name
            
        Returns:
            SchemaComparisonResult with detailed comparison
        """
        result = SchemaComparisonResult(
            table_name=source.table_name,
            source_env=source_env,
            target_env=target_env,
            source_host=source.database_host,
            target_host=target.database_host,
        )
        
        # Compare columns
        self._compare_columns(source, target, result)
        
        # Compare primary key
        self._compare_primary_key(source, target, result)
        
        # Compare indexes (semantic)
        self._compare_indexes(source, target, result)
        
        # Compare foreign keys (semantic)
        self._compare_foreign_keys(source, target, result)
        
        # Compare check constraints (semantic)
        self._compare_check_constraints(source, target, result)
        
        # Calculate totals
        result.total_differences = (
            len(result.column_differences) +
            len(result.index_differences) +
            len(result.fk_differences) +
            len(result.check_differences) +
            (0 if result.pk_match else 1)
        )
        
        result.is_match = result.total_differences == 0
        
        return result
    
    def _compare_columns(
        self,
        source: TableSchema,
        target: TableSchema,
        result: SchemaComparisonResult
    ) -> None:
        """Compare column schemas."""
        source_cols = set(source.columns.keys())
        target_cols = set(target.columns.keys())
        
        # Columns missing in target
        for col_name in source_cols - target_cols:
            result.column_differences.append(ColumnDifference(
                column_name=col_name,
                difference_type='missing_in_target',
                source_value=source.columns[col_name].data_type,
            ))
        
        # Columns missing in source
        for col_name in target_cols - source_cols:
            result.column_differences.append(ColumnDifference(
                column_name=col_name,
                difference_type='missing_in_source',
                target_value=target.columns[col_name].data_type,
            ))
        
        # Compare common columns
        for col_name in source_cols & target_cols:
            source_col = source.columns[col_name]
            target_col = target.columns[col_name]
            
            matches, differences = source_col.matches(target_col, strict=self.strict)
            
            if not matches:
                result.column_differences.append(ColumnDifference(
                    column_name=col_name,
                    difference_type='mismatch',
                    source_value=source_col.data_type,
                    target_value=target_col.data_type,
                    details=differences,
                ))
        
        result.columns_match = len(result.column_differences) == 0
    
    def _compare_primary_key(
        self,
        source: TableSchema,
        target: TableSchema,
        result: SchemaComparisonResult
    ) -> None:
        """Compare primary key definitions."""
        result.source_pk = source.primary_key
        result.target_pk = target.primary_key
        result.pk_match = source.primary_key == target.primary_key
    
    def _compare_indexes(
        self,
        source: TableSchema,
        target: TableSchema,
        result: SchemaComparisonResult
    ) -> None:
        """Compare indexes semantically (ignoring names)."""
        source_sigs = {idx.signature(): idx for idx in source.indexes}
        target_sigs = {idx.signature(): idx for idx in target.indexes}
        
        # Indexes missing in target
        for sig, idx in source_sigs.items():
            if sig not in target_sigs:
                result.index_differences.append(IndexDifference(
                    difference_type='missing_in_target',
                    index_columns=idx.columns,
                    is_unique=idx.is_unique,
                    index_type=idx.index_type,
                    source_name=idx.name,
                ))
        
        # Indexes missing in source
        for sig, idx in target_sigs.items():
            if sig not in source_sigs:
                result.index_differences.append(IndexDifference(
                    difference_type='missing_in_source',
                    index_columns=idx.columns,
                    is_unique=idx.is_unique,
                    index_type=idx.index_type,
                    target_name=idx.name,
                ))
        
        result.indexes_match = len(result.index_differences) == 0
    
    def _compare_foreign_keys(
        self,
        source: TableSchema,
        target: TableSchema,
        result: SchemaComparisonResult
    ) -> None:
        """Compare foreign keys semantically (ignoring names)."""
        source_sigs = {fk.signature(): fk for fk in source.foreign_keys}
        target_sigs = {fk.signature(): fk for fk in target.foreign_keys}
        
        # FKs missing in target
        for sig, fk in source_sigs.items():
            if sig not in target_sigs:
                result.fk_differences.append(ForeignKeyDifference(
                    difference_type='missing_in_target',
                    columns=fk.columns,
                    referenced_table=fk.referenced_table,
                    referenced_columns=fk.referenced_columns,
                    source_name=fk.name,
                ))
        
        # FKs missing in source
        for sig, fk in target_sigs.items():
            if sig not in source_sigs:
                result.fk_differences.append(ForeignKeyDifference(
                    difference_type='missing_in_source',
                    columns=fk.columns,
                    referenced_table=fk.referenced_table,
                    referenced_columns=fk.referenced_columns,
                    target_name=fk.name,
                ))
        
        result.fks_match = len(result.fk_differences) == 0
    
    def _compare_check_constraints(
        self,
        source: TableSchema,
        target: TableSchema,
        result: SchemaComparisonResult
    ) -> None:
        """Compare check constraints semantically."""
        source_exprs = {c.normalized_expression() for c in source.check_constraints}
        target_exprs = {c.normalized_expression() for c in target.check_constraints}
        
        for expr in source_exprs - target_exprs:
            result.check_differences.append(f"Missing in target: {expr}")
        
        for expr in target_exprs - source_exprs:
            result.check_differences.append(f"Missing in source: {expr}")
        
        result.checks_match = len(result.check_differences) == 0
