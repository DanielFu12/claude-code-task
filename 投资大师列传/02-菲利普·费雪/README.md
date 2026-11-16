# 02 · 菲利普·费雪：寻找伟大的成长股

- 竖屏成片：`菲利普·费雪：寻找伟大的成长股（竖屏）.mp4`（1080×1920 · 30fps · 约 4:51 · H.264 CRF 24 `-tune grain` + AAC 192k），`./build_r.sh` 生成
- 脚本：`脚本.md`（由 `src/shots.py` 生成，不要手改）。62 个镜头，10 章 + 片尾
- 形式与版式：按 `投资大师列传/制作规范.md`，代码以第 01 集为模板
- 品牌：**MastersTao**（右上角官方 logo、底部关注语胶囊、MastersTao 品牌片尾）

## 画面素材：真实历史照片（不用 AI 生成）

按用户要求，本集不用 Gemini 生成示意图，全部改用 **Wikimedia Commons 上的公有领域 / 自由授权照片**（`assets/*.jpg`，1280 宽，JPEG q88）。来源清单见 `assets/credits.json`，重新下载：`python3 src/assets.py`。

选图原则：
- 只用公有领域、CC0、CC BY、CC BY-SA；
- 不用与费雪无关、但能看清面部、容易被误认成他本人的人像（例如 1920 年代报童特写、1930 年代办公室合影都已换掉）；
- 照片是「时代示意」，不是费雪本人或其公司的照片：例如 `office1931` 是 1930 年代赫尔辛基的办公室，`fmc` 是 1920 年代的店铺内景，`transistor` 是穆拉德（Mullard）早期晶体管而不是德州仪器的产品。

**署名要求**：CC BY / CC BY-SA 的图（`transistor`、`stamp`、`son1979`、`old_desk`、`sanmateo`、`goldengate`）发布时需要署名，建议放在视频简介里，例如「部分画面来自 Wikimedia Commons：Andy Dingley（CC BY-SA 3.0）、Mannequin（CC BY 2.0）、Jawed（CC BY-SA 3.0）、Thomas Quine（CC BY 2.0）、Jazzflautista（CC BY-SA 4.0）、Frank Schulenburg（CC BY-SA 4.0）」。

| 画面 | 来源 | 授权 | 作者 |
|---|---|---|---|
| `sf1907` | [Italian American Bank, 1907, corner of Sacramento and Montgomery Stree](https://commons.wikimedia.org/wiki/File:Italian_American_Bank,_1907,_corner_of_Sacramento_and_Montgomery_Streets,_San_Francisco.png) | Public domain | Turrill & Miller, San Francisco History Cente |
| `grandma` | [Victorian Parlor](https://commons.wikimedia.org/wiki/File:Victorian_Parlor.jpg) | Public domain | Family member of JGKlein; author died more th |
| `teen_trade` | [Crowds gathering outside New York Stock Exchange (2)](https://commons.wikimedia.org/wiki/File:Crowds_gathering_outside_New_York_Stock_Exchange_(2).jpg) | Public domain | Associated Press |
| `stanford` | [GENERAL VIEW OF WEST ARCADE - Stanford University Quadrangle, Stanford](https://commons.wikimedia.org/wiki/File:GENERAL_VIEW_OF_WEST_ARCADE_-_Stanford_University_Quadrangle,_Stanford_University_Campus,_Stanford,_Santa_Clara_County,_CA_HABS_CAL,43-STANF,10-7.tif) | Public domain | er |
| `factory_visit` | [INTERIOR, MACHINE SHOP AND STORAGE MEZZANINE, SOUTH SIDE LOOKING SOUTH](https://commons.wikimedia.org/wiki/File:INTERIOR,_MACHINE_SHOP_AND_STORAGE_MEZZANINE,_SOUTH_SIDE_LOOKING_SOUTHWEST_-_Machine_Shop,_Second_Street_and_Dedrick_Drive,_Keyport,_Kitsap_County,_WA_HABS_WA-259-7.tif) | Public domain | Brink, John, creator |
| `car1927` | [004 Model T Ford on Mt Hood Forest road, Zigzgag 1920's (36209290225)](https://commons.wikimedia.org/wiki/File:004_Model_T_Ford_on_Mt_Hood_Forest_road,_Zigzgag_1920%27s_(36209290225).jpg) | Public domain | U.S. Forest Service- Pacific Northwest Region |
| `bank1928` | [1921 - Interior Merchants National Bank - Allentown PA](https://commons.wikimedia.org/wiki/File:1921_-_Interior_Merchants_National_Bank_-_Allentown_PA.jpg) | Public domain | 佚名 |
| `tires` | [Western Tire Company store, southeast corner of Sixth Street and Olive](https://commons.wikimedia.org/wiki/File:Western_Tire_Company_store,_southeast_corner_of_Sixth_Street_and_Olive_Street,_1920-1921_(CHS-299).jpg) | Public domain | 佚名 |
| `ticker1929` | [Crowds gathering outside New York Stock Exchange](https://commons.wikimedia.org/wiki/File:Crowds_gathering_outside_New_York_Stock_Exchange.jpg) | Public domain | Associated Press |
| `broker1930` | [Crowds gathering outside New York Stock Exchange (4)](https://commons.wikimedia.org/wiki/File:Crowds_gathering_outside_New_York_Stock_Exchange_(4).jpg) | Public domain | Associated Press |
| `office1931` | [Office in the Radio House in Fabianinkatu, Helsinki, 1930s](https://commons.wikimedia.org/wiki/File:Office_in_the_Radio_House_in_Fabianinkatu,_Helsinki,_1930s.jpg) | Public domain | Archives of the Finnish Broadcasting Company  |
| `depression` | [Depression, Breadlines-long line of people waiting to be fed, New York](https://commons.wikimedia.org/wiki/File:Depression,_Breadlines-long_line_of_people_waiting_to_be_fed,_New_York_City,_in_the_absence_of_substantial_government..._-_NARA_-_196506.tif) | Public domain | 佚名 or not provided |
| `office_lamp` | [Office in the Radio House in Fabianinkatu, Helsinki, 1930s](https://commons.wikimedia.org/wiki/File:Office_in_the_Radio_House_in_Fabianinkatu,_Helsinki,_1930s.jpg) | Public domain | Archives of the Finnish Broadcasting Company  |
| `fmc` | [Historic American Buildings Survey Ray Malinowski, Photographer July-A](https://commons.wikimedia.org/wiki/File:Historic_American_Buildings_Survey_Ray_Malinowski,_Photographer_July-August_1968_PHOTOCOPY_OF_INTERIOR,_c._1920_-_McKenzie_Oerting_and_Company_Building,_601_South_Palafox_Street_HABS_FLA,17-PENSA,18-5.tif) | Public domain | — |
| `ww2` | [36th Bomb Squadron Fort Glenn AAF June 1942](https://commons.wikimedia.org/wiki/File:36th_Bomb_Squadron_Fort_Glenn_AAF_June_1942.jpg) | Public domain | United States Army Air Forces |
| `radio` | [Radio set assembling room LCCN2016850636](https://commons.wikimedia.org/wiki/File:Radio_set_assembling_room_LCCN2016850636.jpg) | Public domain | National Photo Company Collection |
| `transistor` | [Early Mullard small signal transistor packages](https://commons.wikimedia.org/wiki/File:Early_Mullard_small_signal_transistor_packages.jpg) | CC BY-SA 3.0 | Andy Dingley |
| `book1958` | [Old books on bookshelf. (Unsplash)](https://commons.wikimedia.org/wiki/File:Old_books_on_bookshelf._(Unsplash).jpg) | CC0 | Clem Onojeghuo clemono2 |
| `diner` | [1959 - Plain and Fancy Diner](https://commons.wikimedia.org/wiki/File:1959_-_Plain_and_Fancy_Diner.jpg) | Public domain | 佚名 |
| `handshake` | [Business agreement handshake at coffee shop](https://commons.wikimedia.org/wiki/File:Business_agreement_handshake_at_coffee_shop.jpg) | CC0 | rawpixel.com |
| `stamp` | [Old book - Basking Ridge Historical Society](https://commons.wikimedia.org/wiki/File:Old_book_-_Basking_Ridge_Historical_Society.jpg) | CC BY 2.0 | Mannequin- from Basking Ridge, NJ, USA |
| `locomotive` | [Southern Pacific locomotive 4000](https://commons.wikimedia.org/wiki/File:Southern_Pacific_locomotive_4000.jpg) | Public domain | Edward Mitchell, San Francisco |
| `visit1960s` | [NORTH FRONT - Jackson Square (Commercial Building), 415-431 Jackson St](https://commons.wikimedia.org/wiki/File:NORTH_FRONT_-_Jackson_Square_(Commercial_Building),_415-431_Jackson_Street,_San_Francisco,_San_Francisco_County,_CA_HABS_CAL,38-SANFRA,154-1.tif) | Public domain | — |
| `magazine1969` | [Bookshelf (Unsplash)](https://commons.wikimedia.org/wiki/File:Bookshelf_(Unsplash).jpg) | CC0 | kazuend kazuend |
| `books1975` | [Bookshelf (Unsplash)](https://commons.wikimedia.org/wiki/File:Bookshelf_(Unsplash).jpg) | CC0 | kazuend kazuend |
| `son1979` | [Woodside California 2004](https://commons.wikimedia.org/wiki/File:Woodside_California_2004.jpg) | CC BY-SA 3.0 | Users Jawed, Jawed on en.wikipedia |
| `old_desk` | [Antique writing desk - Casa Loma](https://commons.wikimedia.org/wiki/File:Antique_writing_desk_-_Casa_Loma.jpg) | CC BY 2.0 | Thomas Quine |
| `sanmateo` | [East Palo Alto Bay Trail at Sunset, Don Edwards San Francisco Bay Nati](https://commons.wikimedia.org/wiki/File:East_Palo_Alto_Bay_Trail_at_Sunset,_Don_Edwards_San_Francisco_Bay_National_Wildlife_Refuge.jpg) | CC BY-SA 4.0 | Jazzflautista |
| `analyst_now` | [LOC Main Reading Room Highsmith](https://commons.wikimedia.org/wiki/File:LOC_Main_Reading_Room_Highsmith.jpg) | Public domain | Carol M. Highsmith |
| `study` | [Abbotsford House Study Room](https://commons.wikimedia.org/wiki/File:Abbotsford_House_Study_Room.jpg) | CC0 | Michael D Beckwith |
| `redwood` | [Sun through the redwoods](https://commons.wikimedia.org/wiki/File:Sun_through_the_redwoods.jpg) | Public domain | Jonathon Coombes |
| `goldengate` | [Golden Gate Bridge in light morning fog](https://commons.wikimedia.org/wiki/File:Golden_Gate_Bridge_in_light_morning_fog.jpg) | CC BY-SA 4.0 | Frank Schulenburg |
| `chemical` | [Dow Chemical Company plant in Midland, Michigan - DPLA - 31b068b111a87](https://commons.wikimedia.org/wiki/File:Dow_Chemical_Company_plant_in_Midland,_Michigan_-_DPLA_-_31b068b111a876b6626206e7aa56769f.jpg) | Public domain | Dow Chemical Company |

## 音乐与卡点（`src/music_r.py`）

- 参照片配乐 `assets/music/ref_bgm.m4a`（用户已获使用授权）。拼接 `SEGS = [(0, 188.1), (107.0, 213.2)]`，接缝两边都是重拍，全片约 4:51
- 各章起点（重拍）：序章 0 · 少年与课堂 16.5 · 初入金融 43.6 · 逆势创业 68.5 · 伟大的成长股 95.7 · 成长股的法则 128.5 · 费雪的错误清单 182.0 · 巴菲特的另一位老师 209.6 · 落幕 240.3 · 尾声 257.3 · 片尾 273.4（logo 279.9，文字 282.7）
- 镜头 3.4–6.6 秒，平均约 4.5 秒，没有短于阅读需要 85% 的镜头
- 大落点：逆势创业、伟大的成长股、巴菲特的另一位老师、尾声；错误清单压暗收窄
- 关注语：约 52.2s，收尾 249.5s（带「更多投资大师 · 主页合集」）

## 和脚本相比的调整

- 三句字幕略精简以满足阅读时间：轮胎采购纸卡、闲聊法、三个卖出理由
- 集中持股的圆环图不标具体比例（费雪没有公开的持仓比例数据），只写「三四只 / 占大部分资金」
- 所有数据动画只画趋势，不写倍数和金额（见 `脚本.md` 第三节）

## 发布前

- `脚本.md` 第四节 33 条待核实事项逐条核对（重点：第 22 条「价格与价值」引语的出处、第 24 条择时卖出的具体事例）
- 在视频简介里补上 CC BY / CC BY-SA 图片的署名

## 重新生成

```bash
./build_r.sh
```

出单帧：

```bash
TL=r python3 src/render_v.py still <镜头号> <镜头内秒数> out.png
```
