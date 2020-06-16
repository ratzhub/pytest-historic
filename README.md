# pytest-historic

Pytest-historic is a free, custom html report which provides historical pytest execution results by storing execution results info in MySQL database and generate's html reports (charts / statistics) from database using Flask.

> MYSQL + Flask + pytest

![PyPI version](https://badge.fury.io/py/pytest-historic.svg)
[![Downloads](https://pepy.tech/badge/pytest-historic)](https://pepy.tech/project/pytest-historic)
![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg?style=flat-square)
![Maintenance](https://img.shields.io/badge/Maintained%3F-yes-green.svg)
![Open Source Love png1](https://badges.frapsoft.com/os/v1/open-source.png?v=103)
[![HitCount](http://hits.dwyl.io/adiralashiva8/pytest-historic.svg)](http://hits.dwyl.io/adiralashiva8/pytest-historic)

---

## Pytest Historic Overview

 > <img src="https://i.ibb.co/L8vXqrz/gif.gif" alt="Overview">
 
 More Images [here](https://github.com/adiralashiva8/pytest-historic/wiki/Pytest-Historic-View)

---

## Features

- Support Historic Results
- Visualization of executions
- Search Historical test records by name / status / execution id
- Local hosted (meets privacy concerns)
- Flakiness
- Compare executions
- Generate Pytest-metrics report
- Custom comments on failures (Supports html tags)
- Export results (Excel, CSV, Print, Copy)

---

## Why pytest-Historic

- It is free
- Made by QA
- Can customize as per requirements
- No code changes required

---

## How it Works:

- Get execution details using __hooks__
- Store execution results in local / remote hosted __MySQL__ database
- Generate html report using __Flask__

  > <img src="https://i.ibb.co/bbRdFSx/Pytest-Working.png" alt="pytest-historic-overview">

---

## Requirements

 - Python 3.7 or above
 - Pytest
 - MySQL DB

---

## Installation

 - __Step 1:__ Download and Install MySQL Server - [guide](https://bit.ly/39zw0DF)

  - __Step 2:__ Install pytest-historic

    > Case 1: Using pip
    ```
    pip install pytest-historic==0.1.2
    ```

    > Case 2: Using setup.py (root)
    ```
    python setup.py install
    ```

    > Case 3: Using git (latest changes)
    ```
    pip install git+https://github.com/adiralashiva8/pytest-historic
    ```

 - __Step 3:__ Create *pytesthistoric* default user with permissions - [guide](https://bit.ly/2Ir29BD)

 - __Step 4:__ Create *pytesthistoric.tb_project* table - [guide](https://bit.ly/2wAJpgm)

 - __Step 5:__ Install pytest-historic-hook
    ```
    pip install pytest-historic-hook==0.1.2
    ```

   > _Note:_ Above all actions are one time activities

   ### Help / Command line options

   To view available command line options use `--help`

   ```
   pytesthistoric --help
   ```
---

## How to use in project

 - __Step 1:__ Create project in pytest-historic - [guide](https://bit.ly/2IwTqh3)

 - __Step 2:__ Push execution results to project - [guide](https://bit.ly/38zTp6P)

 - __Step 3:__ Open pytest-historic to view historical results

---

Thanks for using pytest-historic

 - What’s your opinion on this report?
 - What’s the feature I should add?

If you have any questions / suggestions / comments on the report, please feel free to reach me at

 - Email: <a href="mailto:adiralashiva8@gmail.com?Subject=pytest%20historic" target="_blank">`adiralashiva8@gmail.com`</a>
 - LinkedIn: <a href="https://www.linkedin.com/in/shivaprasadadirala/" target="_blank">`shivaprasadadirala`</a>
 - Twitter: <a href="https://twitter.com/ShivaAdirala" target="_blank">`@ShivaAdirala`</a>

---
*Special Thanks To*


*Feedback & Suggestions*

 - [Rahul Parwal](https://www.linkedin.com/in/rahul-parwal/)

---

:star: repo if you like it

> Inspired from [Robotframework-Historic](https://github.com/adiralashiva8/robotframework-historic)

---
