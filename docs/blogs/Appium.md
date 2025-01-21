# APP UI Automation with Appium
Author: Bang Liu

Date: 2024-12-27

## Introduction

In this blog, I'll introduce what is [Appium](https://appium.io/docs/en/latest/) and [Selenium](https://www.selenium.dev/) and how we can utilize them for UI automation.

## Appium for UI Automation

### Appium in a Nutshell

Appium aims to support UI automation of many different platforms (mobile, web, desktop, etc.). Not only that, but it also aims to support automation code written in different languages (JS, Java, Python, etc.). Combining all of this functionality in a single program is a very daunting, if not impossible task!

In order to achieve this, Appium is effectively split into four parts:

- **Appium Core**: defines the core APIs
- **Drivers**: implement connectivity to specific platforms
- **Clients**: implement Appium's API in specific languages
- **Plugins**: change or extend Appium's core functionality

Therefore, in order to start automating something with Appium, you need to:

- Install `Appium` itself
- Install a `driver` for your target platform along with its dependencies
- Install a `client library` for your target programming language
- (Optional) install one or more `plugins`


### Installation
Detailed info about how to install Appium, drivers, clients and plugins can  be found from [its documentation website](https://appium.io/docs/en/latest/quickstart/). 

Below is a very brief overview:

1. First check [system requirements](https://appium.io/docs/en/latest/quickstart/requirements/);
2. Then install Appium

```bash
npm install -g appium
```

3. Then Install driver based on your purpose

For example, if I need to test mac apps, I can install `mac2` driver by:

```bash
appium driver install mac2
```
4. Install client for your preferred programming language

For example, for `Python`, we can install its client by:

```bash
pip install Appium-Python-Client
```


### What is next

You can find more resources from [Ecosystem Overview](https://appium.io/docs/en/latest/ecosystem/).

Check the [official website of Appium](https://appium.io/docs/en/latest/) to learn more!

