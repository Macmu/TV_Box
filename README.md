# 影视源镜像（已去推广）

把饭太硬那条聚合地址里的配置抓下来、复制一份，去掉里面的推广与提示内容，
再用 GitHub Actions 每天自动跟更一次。仓库里只放一个 `tvbox.json`，App 直接填它的 raw 地址。

## 这件事的真实结构（先说清楚，免得白折腾）

| 层 | 内容 | 能不能用脚本去掉 |
| --- | --- | --- |
| 配置 JSON | 98 个真实站点 + 2 个直播源 + 4 个解析 | ✅ 可以，就是本脚本在做的事 |
| 配置里的广告位 | `🐮【免费分享】🐮`、`🐮【更新日期:20261112】🐮`、顶层 `ads` | ✅ 已删 |
| 那个 `spider` | 伪装成 `.jpg` 的加固 jar | ⚠️ 配置层留/删由你定，见下 |

**开屏那两条提示（「本接口免费分享！切勿上当」「正在下载站点域名配置」）不是配置里的文字，
是那个 `spider` jar 在 `Init.init()` 里自己联网画出来的。** 所以：

- 保留 `spider`：站点全部可用，但那两行提示还会从 jar 里冒出来。
- `--drop-spider`：配置最干净，但这个源的站点全是 `csp_*Guard` 这类私有类，只存在于那个 jar，
  删掉后 98 个站点会大面积失效。

我默认**保留** `spider`（先保功能），要更干净的镜像加参数跑一次即可。

## 用法

```bash
# 用默认上游，生成 tvbox.json
python3 sync_tvbox.py

# 只看会删掉什么，不写文件
python3 sync_tvbox.py --dry-run

# 换上游
python3 sync_tvbox.py --src https://example.com/tv.json

# 连 jar 一起删（站点会失效，慎用）
python3 sync_tvbox.py --drop-spider
```

产物：

- `tvbox.json`：给 TVBox / FongMi / 我听听 直接填的配置地址
- `removed.txt`：这次删了什么，留痕方便回看

上游没有实质变化时脚本不写文件，Actions 因此不会产生空提交。

## 挂到 GitHub 自动跟更

1. 新建一个公开仓库（公开才能用 raw 直链，App 里不用带 token）。
2. 把本目录的 `sync_tvbox.py`、`.github/workflows/sync.yml` 提交进去。
3. 仓库设置 → Actions → General → Workflow permissions 选 **Read and write**。
4. 手动跑一次 Actions（Actions 页 → 同步影视源 → Run workflow），让它生成首个 `tvbox.json`。

之后每天北京时间 08:10 自动跑，上游一变就提交，提交信息带 UTC 时间。

## App 里怎么填

在「设置 → 源配置 → 影视源」填镜像的 raw 地址：

```
https://raw.githubusercontent.com/<你的账号>/<仓库名>/main/tvbox.json
```

这个地址同时给影视和直播用（配置里 `sites` 和 `lives` 在一份文件里）。

## 已知取舍

- 删掉的只有 2 个广告位站点和 `ads` 字段，**其余 98 个站点原样保留**，不碰 `ext`（那是站点参数，删了会直接失效）。
- `🐮配置┃中心🐮`、`🐮我的┃网盘🐮`、`推送` 这几个我保留了：它们是功能入口，不是公告位。要一并删就改脚本里的 `PROMO_WORDS` 或加 key 黑名单。
- 上游若改成加密/纯 16 进制返回（现存 CDN 里就有一个这样的地址），脚本会直接报「上游不是 JSON」并退出，不会写出半截文件。
