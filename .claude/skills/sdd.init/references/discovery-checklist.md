# Deep Project Discovery Checklist

Thoroughly explore the project to understand it before writing anything. You MUST gather
evidence for every category below. Do not guess — read actual files.
If legacy files were identified, read them for context but do NOT use their patterns as the project standard.

---

## 5.1 Project Identity
- Detect the tech stack: language, framework, build tool, package manager
- Read `README.md`, `package.json`, `build.gradle`, `pom.xml`, `Cargo.toml`, `go.mod`, or equivalent
- Identify if it's a monorepo or single project
- Note the runtime (Node.js, JVM, Go, Python, etc.)

## 5.2 Architecture
- Map the folder structure (top-level and one level deep inside `src/`)
- Identify the architectural pattern (Clean Architecture, MVC, Hexagonal, module-based, etc.)
- Find dependency rules (e.g., ArchUnit, ESLint boundaries, module boundaries)
- Note the separation of layers/modules and their responsibilities
- Look for dependency injection patterns (Spring, NestJS providers, manual wiring, etc.)

## 5.3 Code Conventions
- Read 3-5 representative source files per layer/module to identify patterns
- Note naming conventions (camelCase vs snake_case, file naming, class naming)
- Identify DTO patterns, error handling patterns, validation approach
- Check for linting/formatting config (`.eslintrc`, `.prettierrc`, `checkstyle.xml`, etc.)
- Identify how public contracts are defined (interfaces, schemas, types)

## 5.4 Testing
> **Conditional**: Skip this sub-step if the user indicated they do NOT want testing documentation.

- Find the test directories and test runner configuration
- Read 2-3 test files to understand the testing style and tools
- Identify testing strategy per layer (unit, integration, e2e)
- Note coverage requirements if any
- Find the command to run tests
- Cross-reference findings with the user's testing preferences (coverage targets, layers to focus on,
  clarifications) to identify gaps or alignment between what exists and what the user wants.

## 5.5 Database
- Look for migration files (Flyway, Liquibase, Prisma, Knex, Alembic, etc.)
- Read schema definitions or entity/model files to understand the data model
- Build a mental model of the entity relationships
- Note migration naming conventions

## 5.6 Configuration & Execution
- Find environment variable definitions (`.env.example`, config files, docker-compose)
- Identify how to start the project (dev, prod, docker)
- Note key infrastructure dependencies (databases, message queues, external APIs)

## 5.7 Business Domain
- Identify the core domain entities and their relationships
- Read any existing business documentation
- Note domain-specific terminology that an agent needs to understand
- Understand the main workflows/use cases

## 5.8 API Surface (if applicable)
- Find API route definitions or controller files
- Note API conventions (REST, GraphQL, RPC)
- Check for API documentation (OpenAPI, Swagger, Postman/Hoppscotch collections)
- Note request/response patterns and serialization conventions
