# Background

本项目的目标是通过自动化脚本一键识别、提取 Java SpringBoot 项目的所有路由信息，方便识别、梳理代码审计的工作量，并统计审计进度和覆盖率。

The goal of this project is to use automated scripts to identify and extract all routing information of the Java SpringBoot project in one click, to facilitate the identification and sorting of code audit workload, and to count audit progress and coverage.

# Implement

截至 20240829，已实现 SpringBoot 项目如下相关路由信息的收集：

1. 项目级上下文 context；
2. 类级别的父级路由 parent_route；
3. 函数级的子路由；
4. 路由对应接口支持的 HTTP 请求类型；
5. 路由对应函数的返回值、函数名、函数具体参数；
6. 路由定义所在的类的具体路径信息；

以 [WebGoat](https://github.com/WebGoat/WebGoat) 项目为例，具体的效果图如下（也可参见本项目的效果演示 xlsx 文件）：

![在这里插入图片描述](https://i-blog.csdnimg.cn/direct/80671422f0c54c058584f884fa46a370.png)

详细实现信息请参见我的博客：[SpringBoot项目路由信息自动化提取脚本](https://blog.csdn.net/weixin_39190897/article/details/141689634)。

# How to use

执行命令：

```shell
python scan_routes.py
```

然后输入你本地保存的 SpringBoot 项目源码的根路径即可，比如'D:\Code\Java\WebGoat-2023.8'（支持路径下包含多个项目，可同时扫描），随后会自动进行扫描并输出统计表格。

# Update

- 20240829，首版本开发完成；
- 20240830，修复父级路由识别的已知Bug；
- 20240831，添加对多个项目同时扫描的功能；

# More

本项目实现了对 Java SpringBoot 项目一键自动化识别、统计路由信息，并生成可视化的统计表格，此类项目在 Github 上较少，故开源代码为社区做点微薄贡献。因当前的实验数据并不是很多，其它 Java 源代码项目中也可能出现不适配的情况，后续有时间的话会持续优化、完善，欢迎提交 issues。
