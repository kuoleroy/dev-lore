# 字体

仓库**不带字体文件**（体积 + 授权），需要哪个自己下下来放进这个目录。
`ink` 用思源黑/Noto 不用管，`huge` 需要铁蒺藜，毛笔线需要下面三个里的任意一个。

| 文件名 | 字体 | 用途 | 从哪来 |
|---|---|---|---|
| `TiejiliSC-Regular.ttf` | 铁蒺藜体 | `huge` 巨字（这款带 hinting，libass 认） | 作者三言，搜索「铁蒺藜体 字体」；猫啃网 / 字体天下有下载 |
| `Ma Shan Zheng Regular.ttf` | 马善政毛笔楷 | 毛笔线（楷书，端正） | Google Fonts「Ma Shan Zheng」，SIL OFL 1.1 |
| `ZhiMangXing-Regular.ttf` | 志莽行书 | 毛笔线（行草，狂放） | Google Fonts「Zhi Mang Xing」，SIL OFL 1.1 |

放好之后：

- `huge` 等走 **libass 字体查找**的风格，需要字体**装在系统里**（双击安装），
  只放这个目录不够 —— libass 走 fontconfig，不认当前目录。
- `brush_render.py` 走的是**直接读 ttf 轮廓**，文件放在这里就行，不用安装。
  这也正是它存在的理由：施工机器 fontconfig 坏了的时候，libass 一个书法字体都加载不出来。

字体没装上时不会报错，libass 会静默回退成默认黑体 —— 看着"怎么没效果"，
先确认字体装没装。用 `render.py --preview` 截一帧最快看出来。
