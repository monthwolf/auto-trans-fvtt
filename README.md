
![25c7a33d11864f5c897bf2f943200d61 png~tplv-0es2k971ck-image](https://github.com/monthwolf/auto-trans-fvtt/assets/52775320/eaa88f09-35da-4ee9-a97b-0ce505049a48)

# FVTT合集包自动化翻译 - Auto-Trans-FVTT
> 适用于`babele`生成的合集翻译映射的自动化翻译程序，目前支持deepl、chatgpt和google-gemini三种翻译模式
> 项目灵感来源于[5etools-translated.github.io](https://github.com/5etools-translated/5etools-translated.github.io)

## 更新
- [x] 添加谷歌AI翻译
- [x] 添加语段切分函数
   > 避免内容过长导致AI翻译出错，能够更好地翻译日志规则等长文本内容

## 待办

- [ ] 不依赖babele的通用合集包json汉化

## 介绍
这是一个辅助fvtt合集翻译的程序，本程序旨在自动化翻译合集文本内容，为翻译人士提供便利，有效减少翻译时间成本。  
目前程序支持两种翻译方式，各有各的优点和缺陷：  
- **Deepl:** Deepl的机翻质量比较优秀，程序允许添加[术语表]("#")，翻译的不定性较低，由于是网页模拟操作进行翻译，不需要使用api，降低了使用门槛，但翻译速度比较慢，并且翻译内容比较僵硬，错译较多。
- **Chatgpt:** Chatgpt的翻译质量可以说是比较优秀的，在程序中已经内置了一段提示词，使翻译内容更符合DND语言，gpt的翻译速度会快很多，但是尽管有提示词进行约束，gp翻译的过程中经常会丢失小部分引用，并且由于是调用api进行翻译，需要自行去官网或代理站**购买**gpt翻译额度

## 程序使用方法
首先简单介绍一下项目中的几个内容
```bash
auto-trans-fvtt          项目根目录
├── data                 翻译源文件存储目录
├── data.zh              翻译后的文件存储目录
├── .env                 环境变量配置文件
├── requirements.txt     python依赖文件
├── trans-comp.py        翻译程序文件
├── trans-comp-edge.py   适用于电脑的翻译程序文件
└── translation          翻译辅助文件夹
    ├── cache            翻译映射缓存文件夹
    │   └── zh           中文翻译缓存
    └── glossary         术语表文件夹

```
将翻译`JSON`文件放在`data`目录下，然后就可以进行翻译了
### 本地使用
- 准备:
    - 在命令行运行命令`pip install -r requirements.txt`（运行该步骤请确保你已配置过python环境）
- 基本使用:
    - 运行命令 `python trans-comp.py --deepl --translate data/*.json`，程序将使用deepl开始翻译
- 进阶使用:  
    **使用Chatgpt翻译**:使用chatgpt进行翻译，需要先在`.env`文件中修改环境变量，配置好gpt请求接口后再运行程序
    **翻译程序参数：**
    | 参数             | 类型     | 默认值     | 描述                                           |  
  |-----------------|---------|----------|-----------------------------------------------|
  | `--language`    | str     | 'zh'     | 设置翻译目标语言                               |
  | `--translate`   | bool    | False     | 是否直接翻译文件                                |
  | `--deepl`       | bool    | False    | 是否使用 DeepL 进行翻译 （和ai翻译二选一）       |
  | `--ai`         | str    | False    |  使用`gpt`或者`google`进行AI翻译       |
  | `--maxrun`      | int     | False   | 最大运行时间，单位为秒                    |
   | `--maxlen`      | int     | 3000   | 每段切分文字的最大长度                    |
  | `--recheck-words` | str    | []      | 指定需要重新检查的翻译列表                           |
  | `files`         | str     |          | 指定程序翻译的文件路径，可以使用通配符*                               |
  
  例如对于加载缓存的限时gpt翻译，可以使用命令`python trans-comp.py --ai gpt --translate --maxrun 18000 data/*.json`
> 推荐配合fvtt模组[`foundryvtt-babele-translation-files-generator`](https://github.com/DjLeChuck/foundryvtt-babele-translation-files-generator)一起使用，可以使用我的[fork](https://github.com/monthwolf/foundryvtt-babele-translation-files-generator)版本，加入了文件夹名称映射，也将原项目未merge的修复push合并了
> 该mod依赖于babele，主要功能为快速生成babele翻译文件映射，演示如下：  
> ![bandicam 2024-03-12 23-14-46-713](https://github.com/monthwolf/auto-trans-fvtt/assets/52775320/671cf6cb-95da-422a-a79d-d4ea40517428)


### Github工作流使用
todo

### 翻译展示
以下冒险采用gpt翻译，耗时大概几分钟，效率很高
<img width="1280" alt="image" src="https://github.com/monthwolf/auto-trans-fvtt/assets/52775320/a709e3d2-7622-4c08-84d4-7199c81932e6">
<img width="1280" alt="image" src="https://github.com/monthwolf/auto-trans-fvtt/assets/52775320/131c6dbf-74f5-4d8f-980a-3001d4f67185">
<img width="1280" alt="image" src="https://github.com/monthwolf/auto-trans-fvtt/assets/52775320/6fefacdd-fe01-45c8-a21a-2b4b113abeec">






## 问题反馈
任何程序问题和改进建议，欢迎在[issues](https://github.com/DjLeChuck/foundryvtt-babele-translation-files-generator)中提供反馈！
