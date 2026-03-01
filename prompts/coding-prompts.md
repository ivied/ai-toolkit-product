# 🧑‍💻 Coding Prompts

## Code Review

```
Review this code for: bugs, security issues, performance problems, and readability.
For each issue: describe the problem, explain the risk (low/medium/high),
and provide the fixed code. Format as a table.

Code:
[paste code]
```

## Debug Helper

```
I'm getting this error: [paste error]

In this code: [paste code]

1. Explain what the error means
2. Identify the root cause
3. Provide the fix with explanation
4. Suggest how to prevent this class of bug
```

## Refactoring

```
Refactor this code following these principles:
- Single Responsibility Principle
- DRY (Don't Repeat Yourself)
- Early returns over nested conditions
- Meaningful variable names
- Add type hints (Python) / TypeScript types

Keep the same functionality. Show before/after diff.

Code:
[paste code]
```

## Architecture Design

```
Design the architecture for: [describe system]

Include:
1. Component diagram (text/ASCII)
2. Data flow between components
3. Technology choices with justification
4. API contract (key endpoints)
5. Database schema (key tables/collections)
6. Scalability considerations
7. Potential failure points and mitigations
```

## Test Generation

```
Generate comprehensive tests for this code:

[paste code]

Include:
- Unit tests for each function/method
- Edge cases (empty input, null, overflow, Unicode)
- Error handling tests
- Integration test outline
- Use [pytest/jest/etc.] syntax
- Add descriptive test names
```

## SQL Optimization

```
Optimize this SQL query for performance:

[paste query]

Table sizes: [approximate row counts]
Existing indexes: [list indexes]

Provide:
1. Explain the execution plan issues
2. Optimized query
3. Recommended indexes
4. Expected improvement estimate
```

## API Design

```
Design a REST API for: [describe feature]

For each endpoint provide:
- Method + Path
- Request body/params (with types)
- Response body (with types)
- Status codes
- Auth requirements
- Rate limiting suggestion
- Example curl command

Follow RESTful conventions and use consistent naming.
```
