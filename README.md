# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/CabbageDevelopment/qasync/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                       |    Stmts |     Miss |   Cover |   Missing |
|--------------------------- | -------: | -------: | ------: | --------: |
| src/qasync/\_\_init\_\_.py |      528 |      105 |     80% |33-51, 57-58, 71, 124-158, 188, 190, 214, 233, 236, 243, 275-277, 281-283, 286, 328-331, 387, 396-404, 413, 437, 481, 553, 709-715, 728, 747-763, 767-777, 781-795, 825-828, 846-847, 850, 856-862, 871-874, 934-935 |
| src/qasync/\_common.py     |       10 |        1 |     90% |        22 |
| src/qasync/\_unix.py       |      140 |       77 |     45% |32, 42, 59, 72-78, 81-108, 111-114, 117-120, 123-139, 142-153, 161, 179-182, 186-192, 220-233 |
| src/qasync/\_windows.py    |      150 |       43 |     71% |19-20, 50-53, 74-78, 96-97, 100-101, 104-105, 112-113, 116-117, 120-121, 124-125, 139, 141, 147, 159-164, 167, 170, 174, 198-207 |
| tests/test\_qeventloop.py  |      602 |       52 |     91% |47, 53-54, 158, 207-211, 271, 330-356, 364, 368, 398-403, 622-623, 669-670, 693, 709, 728, 947-956, 967-968 |
| tests/test\_qthreadexec.py |       58 |        1 |     98% |        68 |
| tests/test\_run.py         |       69 |        0 |    100% |           |
|                  **TOTAL** | **1557** |  **279** | **82%** |           |


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