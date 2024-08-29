# Background

本项目的目标是通过自动化脚本一键识别、提取 Java SpringBoot 项目的所有路由信息，方便识别、梳理代码审计的工作量，并统计审计进度和覆盖率。

The goal of this project is to use automated scripts to identify and extract all routing information of the Java SpringBoot project in one click, to facilitate the identification and sorting of code audit workload, and to count audit progress and coverage.

# Implement

详细实现信息参见我的博客：[SpringBoot项目路由信息自动化提取脚本](https://blog.csdn.net/weixin_39190897/article/details/141689634)。

For detailed implementation information, see my blog: [SpringBoot project routing information automatic extraction script](https://blog.csdn.net/weixin_39190897/article/details/141689634).

截至 20240829，已实现 SpringBoot 项目如下相关路由信息的收集：

1. 项目级上下文 context；

2. 类级别的父级路由 parent_route；

3. 函数级的子路由；

4. 路由对应接口支持的 HTTP 请求类型；

5. 路由对应函数的返回值、函数名、函数具体参数；

6. 路由定义所在的类的具体路径信息；

The following relevant routing information of SpringBoot project has been collected:

1. Project context context;

2. Parent routing parent_route at class level;

3. Child routing at function level;

4. HTTP request types supported by the routing corresponding interface;

5. Return value, function name, and specific function parameters of the routing corresponding function;

6. Specific path information of the class where the routing definition is located;

以 [WebGoat](https://github.com/WebGoat/WebGoat) 项目为例，具体的效果图如下（也可参见本项目的效果演示 xlsx 文件）：

Taking the [WebGoat](https://github.com/WebGoat/WebGoat) project as an example, the specific effect diagram is as follows (You can also refer to the effect demonstration xlsx file of this project):

![在这里插入图片描述](https://i-blog.csdnimg.cn/direct/c10fb14f3b6c4243bb959117fa6f40e1.png)

# How to use

执行命令：

```shell
python scan_routes.py
```

然后输入你本地保存的 SpringBoot 项目源码的根路径即可，比如'D:\Code\Java\WebGoat-2023.8'，随后会自动进行扫描并输出统计表格。

Execute the command "python scan_routes.py", and then enter the root path of the SpringBoot project source code you saved locally, such as 'D:\Code\Java\WebGoat-2023.8', and then it will automatically scan and output the statistical table.

# More

本项目实现了对 Java SpringBoot 项目一键自动化识别、统计路由信息，并生成可视化的统计表格，此类项目在 Github 上当前基本找不到开源参考代码仓，也算是为开源社区做点贡献了。当然了，初版代码因为当前的实验数据并不是很多，后期在其它 Java 源代码项目中也可能出现不适配的情况，后续有时间的话会持续优化、完善，欢迎提交 issues。

This project realizes one-click automatic identification and statistics of routing information for Java SpringBoot projects, and generates visual statistical tables. Such projects are currently difficult to find open source reference code repositories on Github, so it can be regarded as a contribution to the open source community. Of course, the initial version of the code may not be compatible with other Java source code projects in the future because there is not much experimental data at present. I will continue to optimize and improve it if I have time. You are welcome to submit issues.
