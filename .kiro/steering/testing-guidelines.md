---
inclusion: always
---

# Testing Guidelines for Task Completion

## Overview

After completing each task in the backend rebuild, you MUST validate the implementation with appropriate tests before marking the task as complete. This ensures we catch issues early and maintain code quality throughout development.

## Testing Approach by Task Type

### Database Models and Foundation

When implementing database models, create a temporary test script that validates:

1. **Import Tests**: All modules can be imported without errors
2. **Model Structure**: Models have required attributes (id, created_at, updated_at, __tablename__)
3. **Relationships**: All relationships are properly defined and bidirectional
4. **Enums**: Enum types are correctly defined with expected values
5. **Table Names**: Table names follow naming conventions
6. **Reserved Names**: No SQLAlchemy reserved names (like `metadata`) are used as column names

**Example Test Script Structure:**
```python
def test_imports():
    """Test all modules can be imported."""
    from module import Class
    assert hasattr(Class, 'expected_attribute')

def test_relationships():
    """Test relationships are defined."""
    from db.models import Model
    assert hasattr(Model, 'relationship_name')

def main():
    tests = [test_imports, test_relationships]
    results = [test() for test in tests]
    print(f"Passed: {sum(results)}/{len(results)}")
```

### API Endpoints

When implementing API endpoints, test:

1. **Route Registration**: Endpoints are properly registered
2. **Request/Response Models**: Pydantic models validate correctly
3. **Dependencies**: FastAPI dependencies work as expected
4. **Error Handling**: Proper error responses for invalid inputs

### Services and Business Logic

When implementing services, test:

1. **Function Signatures**: All required functions are exported
2. **Error Handling**: Exceptions are properly raised and handled
3. **Integration Points**: Services can interact with dependencies

### Configuration

When implementing configuration, test:

1. **Settings Loading**: Configuration loads from environment
2. **Default Values**: Defaults are sensible
3. **Validation**: Invalid values are rejected
4. **Type Checking**: Types are correctly enforced

## Common Issues to Check

### SQLAlchemy Reserved Names

**CRITICAL**: Never use these as column names:
- `metadata` - Use `{model}_metadata` instead (e.g., `platform_metadata`, `message_metadata`)
- `registry`
- `mapper`
- `class_`

### Import Cycles

Check for circular imports by:
1. Importing each module independently
2. Verifying no ImportError occurs
3. Testing in fresh Python interpreter

### Missing Dependencies

Ensure all imports are available:
```python
try:
    from module import Class
except ImportError as e:
    print(f"Missing dependency: {e}")
```

## Test Execution Pattern

1. **Create Test File**: `test_{feature}.py` in the same directory
2. **Run Tests**: Execute with `python test_{feature}.py`
3. **Verify Results**: All tests must pass
4. **Clean Up**: Delete test file after validation
5. **Mark Complete**: Only mark task complete after tests pass

## Test File Template

```python
"""
Test script for {feature} implementation.

Validates:
- {validation point 1}
- {validation point 2}
- {validation point 3}
"""

import sys
from pathlib import Path

# Add backend to path if needed
sys.path.insert(0, str(Path(__file__).parent))

def test_feature_1():
    """Test description."""
    print("Testing feature 1...")
    try:
        # Test code here
        print("  ✓ Feature 1 works")
        return True
    except Exception as e:
        print(f"  ✗ Feature 1 failed: {e}")
        return False

def main():
    """Run all tests."""
    print("=" * 60)
    print("Feature Test Suite")
    print("=" * 60)
    
    tests = [test_feature_1]
    results = [test() for test in tests]
    
    print("\n" + "=" * 60)
    print(f"Passed: {sum(results)}/{len(results)}")
    
    if sum(results) == len(results):
        print("\n✓ All tests passed!")
        return 0
    else:
        print(f"\n✗ {len(results) - sum(results)} test(s) failed.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
```

## When to Skip Testing

Testing can be skipped for:
- Documentation-only changes
- Configuration file updates (unless they affect runtime)
- Minor text/comment changes

## Diagnostic Tools

Use `getDiagnostics` tool to check for:
- Syntax errors
- Type errors
- Import errors
- Linting issues

**Example:**
```python
# After creating files, run:
getDiagnostics(paths=["path/to/file1.py", "path/to/file2.py"])
```

## Integration with Task Workflow

1. **Implement Task**: Write code for the task
2. **Run Diagnostics**: Check for syntax/type errors
3. **Create Test**: Write validation test script
4. **Execute Test**: Run test and verify all pass
5. **Fix Issues**: Address any failures
6. **Clean Up**: Delete test file
7. **Mark Complete**: Update task status to completed

## Benefits

- **Early Detection**: Catch issues immediately after implementation
- **Confidence**: Know that code works before moving forward
- **Documentation**: Tests serve as usage examples
- **Regression Prevention**: Ensure changes don't break existing functionality
- **Quality**: Maintain high code quality throughout development

## Remember

- Tests should be **quick** to write and run
- Tests should be **focused** on the specific task
- Tests should be **deleted** after validation (not committed)
- Tests should **pass** before marking task complete
- Use **getDiagnostics** first for syntax/type checking
- Create **temporary test scripts** for runtime validation
