# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/CabbageDevelopment/qasync/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                       |    Stmts |     Miss |   Cover |   Missing |
|--------------------------- | -------: | -------: | ------: | --------: |
| src/qasync/\_\_init\_\_.py |      518 |      129 |     75% |33-51, 57-58, 71, 124-158, 188, 190, 214, 233, 236, 243, 281-283, 286, 328-331, 380-388, 394, 418, 462, 507, 620-628, 653-659, 672, 691-707, 711-721, 725-739, 769-772, 790-791, 794, 800-806, 812-849, 880-881 |
| src/qasync/\_common.py     |       10 |        1 |     90% |        22 |
| src/qasync/\_unix.py       |      123 |       71 |     42% |28, 38, 54, 67-73, 76-97, 100-103, 106-109, 112-128, 131-142, 164-167, 185-198 |
| src/qasync/\_windows.py    |      144 |       43 |     70% |18-19, 46-49, 70-74, 92-93, 96-97, 100-101, 108-109, 112-113, 116-117, 120-121, 135, 137, 143, 155-160, 163, 166, 170, 194-203 |
| tests/test\_qeventloop.py  |      564 |       46 |     92% |46, 52-53, 157, 206-210, 270, 329-355, 363, 367, 397-402, 621-622, 668-669, 692, 708, 727, 898-900, 910-911 |
| tests/test\_qthreadexec.py |       58 |        1 |     98% |        68 |
| tests/test\_run.py         |       69 |        0 |    100% |           |
|                  **TOTAL** | **1486** |  **291** | **80%** |           |


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