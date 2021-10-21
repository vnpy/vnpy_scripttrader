# vn.py框架的脚本交易模块

<p align="center">
  <img src ="https://vnpy.oss-cn-shanghai.aliyuncs.com/vnpy-logo.png"/>
</p>

<p align="center">
    <img src ="https://img.shields.io/badge/version-1.0.0-blueviolet.svg"/>
    <img src ="https://img.shields.io/badge/platform-windows|linux|macos-yellow.svg"/>
    <img src ="https://img.shields.io/badge/python-3.7-blue.svg" />
    <img src ="https://img.shields.io/github/license/vnpy/vnpy.svg?color=orange"/>
</p>

## 说明

ScriptTrader是用于交易脚本执行的功能模块，和其他策略模块最大的区别在于其基于【时间驱动】的【同步逻辑】，也支持在命令行（Jupyter Notebook）中以REPL指令形式的进行交易操作，该模块没有回测功能。

## 安装

安装需要基于2.7.0版本以上的[VN Studio](https://www.vnpy.com)。

直接使用pip命令：

```
pip install vnpy_scripttrader
```

下载解压后在cmd中运行

```
python setup.py install
```
