---
inclusion: always
---

# Kiro Code Length Guidelines

## 🎯 Primary Rule
**NEVER write code files longer than 500 lines**

## 📏 Line Count Guidelines

### Maximum Limits
- **Single File**: 500 lines maximum (hard limit)
- **Critical Limit**: Stop at 400 lines and suggest splitting
- **Ideal Target**: 200-300 lines per file

### What Counts as Lines
- All code lines (including comments and whitespace)
- Does NOT count import statements separately from total
- Measure the complete file output

## 🚨 When Approaching Limits

### At 300+ Lines
**Alert**: "This file is getting large. Consider if we should split it into multiple files."
**Ask**: "Would you like me to break this into smaller modules?"

### At 400+ Lines
**Stop**: "I need to pause - this file is approaching 400 lines."
**Require**: User confirmation to continue OR agreement to split the file
**Suggest**: Specific ways to modularize

### At 500 Lines
**Hard Stop**: "I cannot create files longer than 500 lines."
**Must**: Split into multiple files before continuing

## ✂️ Splitting Strategies

### Code Organization Approaches
- **Feature-based modules** - Split by functionality
- **Layer separation** - UI, logic, data layers
- **Component extraction** - Reusable components
- **Utility separation** - Helper functions in separate files
- **Configuration extraction** - Config/constants files

### Communication Templates

#### Proactive Warning (300+ lines)
```
⚠️ **File Size Alert**: This file is now ~{LINE_COUNT} lines.

Would you like me to split this into multiple focused modules for better maintainability?

Options:
1. Continue in single file (up to 500 line limit)
2. Split into: [specific suggestions based on code]
```

#### Critical Stop (400+ lines)
```
🛑 **Critical Size Reached**: This file is {LINE_COUNT} lines - approaching the 500 line limit.

I need to either:
- Split this into multiple files now
- Get your explicit approval to continue (limited to 100 more lines max)

Suggested split: [specific breakdown]
```

#### Hard Limit (500 lines)
```
❌ **Cannot Exceed 500 Lines**: File size limit reached.

This must be split into multiple files. Here's my recommended structure:
[Provide specific file breakdown with estimated line counts]
```

## 🛠️ Implementation Examples

### Good: Suggest Splits Early
"I notice this service class is getting large (~350 lines). Should I extract the database operations into a separate repository class and the validation logic into utility functions?"

### Good: Offer Specific Solutions
```
This file is approaching 400 lines. I can split it into:
- user_service.py (~200 lines) - Core user operations
- user_validators.py (~150 lines) - Validation logic
- user_utils.py (~100 lines) - Helper functions
```

### Bad Examples ❌
- **Just Warning**: "This file is getting long"
- **Ignoring the Limit**: Continuing to write past 500 lines without stopping

## 🎯 Quality Over Quantity

### Encourage
- Modular design from the start
- Single responsibility per file
- Clear separation of concerns
- Reusable components
- Logical file organization

### Discourage
- Monolithic files
- Mixed responsibilities
- Copy-paste instead of imports
- "Just a few more lines" mentality

## 📋 Checklist for Every Code Response

Before sending code, verify:
- [ ] File is under 500 lines
- [ ] If 300+ lines, offered to split
- [ ] If 400+ lines, required explicit approval or splitting
- [ ] Suggested logical separation if file is large
- [ ] Explained benefits of modular approach

## 🎪 Exception Handling

### Rare Acceptable Cases (Still under 500)
- Configuration files with extensive but necessary data
- Generated code (clearly marked as such)
- Migration files or data transformation scripts

### Never Acceptable
- UI components over 500 lines
- Business logic files over 500 lines
- Service classes over 500 lines
- "Convenience" or "just this once" exceptions

## 🏗️ Project-Specific Splitting Patterns

### FastAPI Applications
```python
# Instead of one large main.py:
api/
├── main.py           # App setup, middleware (~100 lines)
├── dependencies.py   # Dependency injection (~150 lines)
├── routes/
│   ├── auth.py      # Authentication routes (~200 lines)
│   ├── users.py     # User management (~250 lines)
│   └── messages.py  # Message operations (~300 lines)
```

### Service Classes
```python
# Instead of one large service:
services/
├── user_service.py      # Core operations (~200 lines)
├── user_repository.py   # Database layer (~150 lines)
├── user_validators.py   # Validation logic (~100 lines)
└── user_utils.py        # Helper functions (~80 lines)
```

### AI Processing
```python
# Instead of monolithic AI service:
services/ai/
├── base_agent.py        # Abstract base (~150 lines)
├── text_processor.py    # Text processing (~200 lines)
├── embedding_service.py # Embeddings (~250 lines)
├── entity_extractor.py  # Entity extraction (~180 lines)
└── summary_generator.py # Summarization (~220 lines)
```

### Database Models
```python
# Instead of all models in one file:
db/models/
├── base.py         # Base model class (~100 lines)
├── user.py         # User model (~150 lines)
├── message.py      # Message model (~200 lines)
├── thread.py       # Thread model (~120 lines)
└── attachment.py   # Attachment model (~80 lines)
```

## 🔧 Refactoring Guidelines

### When to Split
1. **Single Responsibility Violation**: File handles multiple concerns
2. **High Complexity**: Too many methods/functions in one place
3. **Reusability**: Code that could be shared across modules
4. **Testing Difficulty**: Hard to write focused unit tests

### How to Split
1. **Identify Boundaries**: Look for natural separation points
2. **Extract Utilities**: Move helper functions to separate files
3. **Separate Concerns**: Split business logic from data access
4. **Create Interfaces**: Use abstract base classes for common patterns

### Naming Conventions
- Use descriptive, specific names for split files
- Follow project naming patterns (snake_case)
- Include purpose in filename (e.g., `user_validators.py`)
- Group related files in subdirectories

## 📚 Benefits of Modular Code

### Maintainability
- Easier to understand and modify
- Reduced cognitive load
- Clear separation of concerns

### Testability
- Focused unit tests
- Better test coverage
- Easier mocking and stubbing

### Reusability
- Components can be shared
- Reduced code duplication
- Better abstraction

### Collaboration
- Multiple developers can work simultaneously
- Clearer code ownership
- Reduced merge conflicts

## 🎖️ Best Practices Summary

1. **Plan for Modularity**: Design with separation in mind from the start
2. **Monitor File Size**: Keep track of line counts as you develop
3. **Refactor Early**: Don't wait until files become unwieldy
4. **Use Clear Names**: Make file purposes obvious from their names
5. **Document Decisions**: Explain why files were split in certain ways
6. **Follow Patterns**: Maintain consistency across the project
7. **Test Thoroughly**: Ensure splits don't break functionality

Remember: Clean, modular code is more maintainable, debuggable, and scalable. Enforcing file size limits encourages better architecture from the start and leads to higher quality software.