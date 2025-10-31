# Testing Framework and Validation

## Overview

This topic covers the automated testing framework used to validate the Door Randomizer's generation algorithms, ensuring consistent behavior across different configurations and identifying potential issues with seed generation.

## TestSuite.py - Automated Testing Framework

### Purpose
[`TestSuite.py`](../../TestSuite.py) provides a comprehensive testing framework that runs multiple randomizer configurations in parallel to validate generation success rates and identify problematic settings combinations.

### Core Architecture

#### Parallel Test Execution
The framework utilizes all available CPU cores via [`multiprocessing.cpu_count()`](../../TestSuite.py) and [`concurrent.futures.ThreadPoolExecutor`](../../TestSuite.py) to run tests in parallel, significantly reducing total test execution time.

#### Test Configuration Matrix
The framework tests multiple configuration combinations:
- **Door Shuffle Types**: vanilla, basic, crossed
- **Game Modes**: Open, Standard, Inverted  
- **Intensity Levels**: Variable based on shuffle type
- **Logic Types**: vanilla, keysanity, shopsanity, etc.

### Key Functions

#### [`main(args)`](../../TestSuite.py:12)
- Main test execution function
- Coordinates parallel test runs
- Collects and reports success/failure statistics
- Generates error logs for failed seeds

#### [`test(testname, command)`](../../TestSuite.py:26)
- Creates test configurations for a specific randomizer setting
- Generates tasks for each mode combination (Open/Standard/Inverted)
- Submits tasks to thread pool for parallel execution

### Test Categories

#### Test Categories
- **Basic Validation Tests**: Vanilla, Retro, Keysanity, Shopsanity modes
- **Shuffle Algorithm Tests**: Simple, Full, Lite, Lean, Swapped, Crossed, Insanity shuffle types
- **Advanced Logic Tests**: Overworld Glitches logic testing

### Progress Tracking and Reporting

#### Real-time Feedback
Uses `tqdm` progress bars to show:
- Current success rate percentage
- Currently executing test configuration
- Total completed vs remaining tests

#### Success Rate Calculation
The framework tracks both individual test success rates and overall success rates by configuration using the [`tqdm`](../../TestSuite.py) progress tracking system.

#### Error Logging
Failed seeds are logged with:
- Test configuration that failed
- Full command line used
- Complete error output from randomizer

### Test Execution Modes

#### Individual Configuration Testing
Supports custom test counts and thread configuration via command line arguments.

#### Comprehensive Suite Testing
Automatically runs tiered testing:
- **Vanilla**: 2 attempts, intensity 1
- **Basic**: 5 attempts, up to intensity 3  
- **Crossed**: 10 attempts, up to intensity 3

### Integration with Door Randomizer

#### Command Line Interface
Tests execute the main randomizer via [`subprocess.run()`](../../TestSuite.py) with captured output for analysis.

#### ROM Suppression
Uses `--suppress_rom` flag to skip ROM generation and focus on logic validation.

#### Spoiler Suppression  
Uses `--spoiler none` to minimize output and focus on generation success.

### Output and Reporting

#### Success Rate Reports
Provides detailed success rate reports broken down by configuration and game mode (Open/Standard/Inverted).

#### Error File Generation
Creates separate error files for each configuration:
- `vanilla-errors.txt`
- `basic-1-errors.txt` 
- `crossed-3-errors.txt`

#### Summary Statistics
Final report includes:
- Total tests run
- Overall success rates
- Configuration-specific statistics

### Performance Characteristics

#### Scalability
- Automatically detects available CPU cores
- Scales test execution based on hardware capabilities
- Configurable thread count via command line

#### Resource Management
- Uses thread pools for efficient resource utilization
- Captures subprocess output to prevent memory leaks
- Manages concurrent test execution without overwhelming system

### Error Handling and Diagnostics

#### Exception Capture
The framework captures and logs exceptions during test execution, preserving complete error context via the [`task.result()`](../../TestSuite.py) mechanism.

#### Failure Analysis
- Separates generation failures from system errors
- Preserves complete error context for debugging
- Tracks which specific configurations are problematic

### Usage Patterns

#### Development Testing
- Run during development to catch regressions
- Validate new features don't break existing functionality
- Test edge cases and boundary conditions

#### Release Validation
- Comprehensive testing before releases
- Validate cross-platform compatibility  
- Ensure consistent behavior across configurations

#### Performance Benchmarking
- Measure generation success rates
- Identify slow or problematic configurations
- Track performance improvements over time

## Design Considerations

### Reliability
- Parallel execution with proper error isolation
- Comprehensive error logging for debugging
- Statistical validation of randomizer stability

### Maintainability
- Clear separation of test configurations
- Extensible framework for adding new test cases
- Standardized reporting format

### Performance
- Multi-threaded execution for faster testing
- Efficient subprocess management
- Minimal overhead beyond actual generation testing

## Dependencies

- **`multiprocessing`**: CPU core detection and parallel execution
- **`concurrent.futures`**: Thread pool management
- **`subprocess`**: Randomizer execution
- **`tqdm`**: Progress bar display
- **`argparse`**: Command line argument parsing

## Related Topics
- [Main Algorithm Flow](main_algorithm_flow.md) - Tests the core generation process
- [Error Handling and Logging](error_handling_and_logging.md) - Validates error reporting
- [Door and Dungeon Shuffling](door_and_dungeon_shuffling.md) - Tests shuffling algorithms
- [Argument and Settings Initialization](argument_and_settings_initialization.md) - Tests CLI parsing