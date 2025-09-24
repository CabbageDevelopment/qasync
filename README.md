# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/CabbageDevelopment/qasync/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                       |    Stmts |     Miss |   Cover |   Missing |
|--------------------------- | -------: | -------: | ------: | --------: |
| src/qasync/\_\_init\_\_.py |      519 |       82 |     84% |105-139, 169, 171, 195, 214, 217, 224, 256-258, 262-264, 267, 309-312, 368, 377-385, 464, 536, 692-698, 711, 730-746, 750-760, 764-778, 808-811, 830-831, 834 |
| src/qasync/\_common.py     |       10 |        1 |     90% |        22 |
| src/qasync/\_unix.py       |      140 |       77 |     45% |32, 42, 59, 72-78, 81-108, 111-114, 117-120, 123-139, 142-153, 161, 179-182, 186-192, 220-233 |
| src/qasync/\_windows.py    |      150 |       43 |     71% |19-20, 50-53, 74-78, 96-97, 100-101, 104-105, 112-113, 116-117, 120-121, 124-125, 139, 141, 147, 159-164, 167, 170, 174, 198-207 |
| tests/test\_environment.py |       56 |        0 |    100% |           |
| tests/test\_qeventloop.py  |      676 |       53 |     92% |48, 54-55, 159, 208-212, 272, 331-357, 365, 369, 399-404, 623-624, 670-671, 694, 710, 729, 900, 1055-1064, 1075-1076 |
| tests/test\_qthreadexec.py |       58 |        1 |     98% |        68 |
| tests/test\_run.py         |       69 |        0 |    100% |           |
|                  **TOTAL** | **1678** |  **257** | **85%** |           |


## Setup coverage badge

Below are examples of the badges you can use in your main branch `README` file.

### Direct image

[![Coverage badge](https://raw.githubusercontent.com/CabbageDevelopment/qasync/python-coverage-comment-action-data/badge.svg)](https://htmlpreview.github.io/?https://github.com/CabbageDevelopment/qasync/blob/python-coverage-comment-action-data/htmlcov/index.html)

This is the one to use if your repository is private or if you don't want to customize anything.

### [Shields.io](https://shields.io) Json Endpoint

[![Coverage badge](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/CabbageDevelopment/qasync/python-coverage-comment-action-data/endpoint.json)](https://htmlpreview.github.io/?https://github.com/CabbageDevelopment/qasync/blob/python-coverage-comment-action-data/htmlcov/index.html)

Using this one will allow you to [customize](https://shields.io/endpoint) the look of your badge.
It won't work with private repositories. It won't be refreshed more than once per five minutes.

### [Shields.io](https://shields.io) Dynamic Badge

[![Coverage badge](https://img.shields.io/badge/dynamic/json?color=brightgreen&label=coverage&query=%24.message&url=https%3A%2F%2Fraw.githubusercontent.com%2FCabbageDevelopment%2Fqasync%2Fpython-coverage-comment-action-data%2Fendpoint.json)](https://htmlpreview.github.io/?https://github.com/CabbageDevelopment/qasync/blob/python-coverage-comment-action-data/htmlcov/index.html)

This one will always be the same color. It won't work for private repos. I'm not even sure why we included it.

## What is that?

This branch is part of the
[python-coverage-comment-action](https://github.com/marketplace/actions/python-coverage-comment)
GitHub Action. All the files in this branch are automatically generated and may be
overwritten at any moment.