# CRO-MAGNON MMO

[日本語](#日本語) · [English](#english)

## 日本語

クロマニョン人の時代をローポリで描いた、ブラウザーで遊べる3Dゲームです。約5万年前の大陸を近似した世界で、草原・雪原・氷床・火山・砂漠を歩き、採集・調理・マンモス狩りをしながら、仲間のマスコットと旅をします。現在はソロプレイ専用で、進行はブラウザーに自動保存されます。

**遊ぶ：[cromagnonmmo.com](https://cromagnonmmo.com/)**（[English](https://cromagnonmmo.com/en/)）

作者: yuri（[@yurinakanishi33](https://x.com/yurinakanishi33)）

### ありがとう

仲間のマスコットとして、3Dモデルでゲームに登場してくれた524（[@R5ni4](https://x.com/R5ni4)さん）とりもねこ（[@vibe_walking](https://x.com/vibe_walking)さん）、ありがとうございます。

洞窟の壁画に出演してくれた皆さん、ありがとうございます。

- [@WabisukeTyper](https://x.com/WabisukeTyper)さん
- [@nukonuko](https://x.com/nukonuko)さん
- [@otani_ai_memo](https://x.com/otani_ai_memo)さん
- [@yuki_urata](https://x.com/yuki_urata)さん
- [@R5ni4](https://x.com/R5ni4)さん
- [@vibe_walking](https://x.com/vibe_walking)さん
- [@marulimoai](https://x.com/marulimoai)さん
- [@mae616_](https://x.com/mae616_)さん
- [@eerm16g](https://x.com/eerm16g)さん
- [@Saber5656](https://x.com/Saber5656)さん
- [@Fairy_Yoshizawa](https://x.com/Fairy_Yoshizawa)さん
- [@Sagasa8045](https://x.com/Sagasa8045)さん
- [@hawkymisc](https://x.com/hawkymisc)さん
- [@asahina_AIauto](https://x.com/asahina_AIauto)さん
- [@daredaro_F](https://x.com/daredaro_F)さん
- [@Jank0vic](https://x.com/Jank0vic)さん
- Dots by [OpenAI](https://x.com/OpenAI)

仲間や壁画に登場する人たちは、ゲームのタイトル画面の「関わってくれた人たち」と、洞窟の「壁画の人々」で紹介しています。

### 一緒に作りませんか

プルリクエスト大歓迎です！特に、新しい機能の追加を待っています。

- 自分のキャラクターを洞窟の壁画に登場させる
- 自分のキャラクターをプレイヤーとして動かせるようにする
- 撫でられる仲間のマスコットにする
- そのほか、自由なアイデアをぜひ

不具合の修正や改善のプルリクエストも受け付けます。

プルリクエストのタイトルと本文は、このREADMEと同じように日本語と英語を併記してください。本文には変更内容・理由・検証結果を両言語で簡潔に書いてください。翻訳ツールも利用できます。詳しくは [参加のしかた](CONTRIBUTING.md) を参照してください。

### 特徴

- 東西4,096 m・南北2,048 mの世界。海岸線は、NOAAの地形データと当時の海面（−68.3 m）から作っています。
- 人物・動物・植物・岩・地形まで、すべての3Dモデルを参照画像からTRELLIS-2のimage-to-3Dで制作し、リグとアニメーションを付けています。
- 人物14人と、524・りもねこ・Dots全9種類の仲間から選べます。
- PC（キーボード・マウス、ゲームパッド）と、スマートフォンの縦持ちに対応しています。
- ソロの進行はブラウザーのWorker内で処理し、IndexedDBに保存します。アカウントは要りません。

### 手元で動かす

Node.js（24.22.1以上の24系か、26.13.0以上の26系）、pnpm 10、WebGL 2に対応したブラウザーが必要です。pnpmは、Corepackの `corepack enable` で使えるようになります（`package.json` の `packageManager` の版が使われます）。Corepackは24系のNode.jsには付いていますが、26系には付いていないので、先に `npm install --global corepack` で入れます。

```bash
pnpm install --frozen-lockfile
pnpm start
```

ブラウザーで http://localhost:3000 を開きます。初回の `pnpm start` は、3Dモデルを配信用に変換するので数分かかります。開発中は `pnpm start` の代わりに `pnpm run dev` を使うと、TypeScriptとCSSの変更を監視して作り直します。

サーバーは、このPC（127.0.0.1）からの接続だけを受け付けます。同じネットワークのスマートフォンなどから開くときは、環境変数 `HOST=0.0.0.0` を付けて起動します（PowerShellでは `$env:HOST='0.0.0.0'; pnpm run dev`）。ポートは環境変数 `PORT` で変えられます（既定は3000）。手元で動かすのに、APIキーなどの秘密の設定は要りません（`.env` のファイルもありません）。

テストと、型・構文・依存の境界の検査、書式の確認：

```bash
pnpm test
pnpm run check
pnpm run format:check
```

環境変数の一覧、任意の制作ツール、秘密情報の混入を検査する `pnpm run audit:oss` は [開発環境](docs/DEVELOPMENT.md) にまとめています。`.env.example` は設定の見本で、起動時に自動では読み込みません。

公開前の全検証（ビルド、テスト、Workerの確認、Google Chromeでの画面の確認）は `pnpm run verify:production` です。Chromeの確認はPlaywrightの `channel: 'chrome'` を使うので、Google Chromeが入っている必要があります。

実行に必要なモデル・画像・音は `public/`、ビルドとテストが使うデータは `assets/` にあります。追加の制作素材を必要とするスクリプトもあり、素材がない場合は対応するテストをスキップします。

### フォルダー構成

| フォルダー        | 内容                                                         |
| ----------------- | ------------------------------------------------------------ |
| `src/`            | ブラウザー側のUI・入力・保存・Three.jsの描画（TypeScript）   |
| `shared/`         | ゲームのルール・移動・当たり判定・世界のデータ・キャラクター |
| `application/`    | 部屋とセッション、操作の調停、送受信するデータの組み立て     |
| `infrastructure/` | Node向けの静的配信と、ソロ用のブラウザーWorker               |
| `cloudflare/`     | 公開サイト（Cloudflare Workers）用                           |
| `public/`         | 配信するHTML・3Dモデル・音・画像                             |
| `assets/`         | 公開用のビルドとテストが読む採用の記録                       |
| `scripts/`        | ビルド・検証・制作のスクリプト                               |
| `tests/`          | 自動テスト（`node:test`）                                    |
| `docs/` | ゲーム仕様・開発手順・構成説明 |

### 文書

文書の多くは日本語で書いています。

- [ゲームの仕様と操作](docs/game-spec.md)
- [公開と主な変更のお知らせ](docs/releases.md)
- [文書の索引](docs/README.md)
- [コードの構成と依存の境界](docs/ARCHITECTURE.md)
- [公開サイトの手順](docs/CLOUDFLARE_DEPLOYMENT.md)

### クレジットとライセンス

制作：中西裕理

プログラム・3Dモデル・画像・音・文書は [Apache License 2.0](LICENSE) で提供しています。登場するキャラクターや壁画のうち、対象外の素材は [NOTICE](NOTICE) に記載しています。ゲームの名前とロゴも対象外です。

一部の3DモデルはMeshmellでCC BY 4.0でも公開しています。外部のライブラリ・データ・音源の条件は [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) にまとめています。

不具合の報告や提案はIssueで受け付けます。プルリクエストは大歓迎です（上の「一緒に作りませんか」と [CONTRIBUTING.md](CONTRIBUTING.md)）。セキュリティの問題は、公開のIssueではなく [SECURITY.md](SECURITY.md) の方法で知らせてください。参加するときは [行動規範](CODE_OF_CONDUCT.md) を守ってください。

## English

A low-poly 3D game set in the age of the Cro-Magnons that you play in the browser. In a world that approximates the continents of about 50,000 years ago, you walk through grasslands, snowfields, ice sheets, volcanoes and deserts, gathering, cooking and hunting mammoths as you travel with mascot companions. For now it is solo only, and your progress is saved automatically in your browser.

**Play: [cromagnonmmo.com](https://cromagnonmmo.com/en/)** ([日本語](https://cromagnonmmo.com/))

Created by yuri ([@yurinakanishi33](https://x.com/yurinakanishi33)).

### Thank you

Thank you to 524 (by [@R5ni4](https://x.com/R5ni4)) and Rimo-neko (by [@vibe_walking](https://x.com/vibe_walking)) for joining the game as 3D models of our mascot companions.

Thank you to everyone who appears in the cave murals.

- [@WabisukeTyper](https://x.com/WabisukeTyper)
- [@nukonuko](https://x.com/nukonuko)
- [@otani_ai_memo](https://x.com/otani_ai_memo)
- [@yuki_urata](https://x.com/yuki_urata)
- [@R5ni4](https://x.com/R5ni4)
- [@vibe_walking](https://x.com/vibe_walking)
- [@marulimoai](https://x.com/marulimoai)
- [@mae616_](https://x.com/mae616_)
- [@eerm16g](https://x.com/eerm16g)
- [@Saber5656](https://x.com/Saber5656)
- [@Fairy_Yoshizawa](https://x.com/Fairy_Yoshizawa)
- [@Sagasa8045](https://x.com/Sagasa8045)
- [@hawkymisc](https://x.com/hawkymisc)
- [@asahina_AIauto](https://x.com/asahina_AIauto)
- [@daredaro_F](https://x.com/daredaro_F)
- [@Jank0vic](https://x.com/Jank0vic)
- Dots by [OpenAI](https://x.com/OpenAI)

The people who appear as companions or in the murals are introduced in the game, under "Contributors" on the title screen and "People in the murals" in the cave.

### Build it with us

Pull requests are very welcome! Above all, I am looking forward to new features.

- Put your own character in the cave murals
- Make your own character playable
- Make it a mascot companion you can pet
- Or any other idea you have

Pull requests that fix bugs or improve things are welcome too.

Please write pull request titles and descriptions in both Japanese and English, as in this README. Briefly describe the changes, reasons and validation results in both languages. You may use translation tools. See [Contributing](CONTRIBUTING.md) for details.

### Features

- A world 4,096 m from east to west and 2,048 m from north to south. The coastlines are made from NOAA terrain data and the sea level of the time (−68.3 m).
- Every 3D model, from people and animals to plants, rocks and terrain, is made from reference images with TRELLIS-2 image-to-3D, and rigged and animated.
- Choose from 14 characters, and from the companions 524, Rimo-neko and all nine Dots.
- Plays on PC (keyboard and mouse, or a gamepad) and on smartphones held upright.
- Solo play runs in a Worker in your browser and is saved to IndexedDB. No account is needed.

### Running it locally

You need Node.js (24.22.1 or later in 24.x, or 26.13.0 or later in 26.x), pnpm 10 and a browser that supports WebGL 2. pnpm becomes available through Corepack's `corepack enable` (the version in `packageManager` in `package.json` is used). Node.js 24.x comes with Corepack but 26.x does not, so install it first with `npm install --global corepack`.

```bash
pnpm install --frozen-lockfile
pnpm start
```

Open http://localhost:3000 in your browser. The first `pnpm start` takes a few minutes because it converts the 3D models for delivery. While developing, use `pnpm run dev` instead of `pnpm start` to watch TypeScript and CSS changes and rebuild.

The server accepts connections only from this PC (127.0.0.1). To open it from a smartphone or another device on the same network, start it with the environment variable `HOST=0.0.0.0` (in PowerShell: `$env:HOST='0.0.0.0'; pnpm run dev`). The environment variable `PORT` changes the port (3000 by default). Running it locally needs no API keys or other secrets (and there is no `.env` file).

Tests, the type, syntax and dependency-boundary checks, and the format check:

```bash
pnpm test
pnpm run check
pnpm run format:check
```

The full check before a release (build, tests, Worker checks and screen checks in Google Chrome) is `pnpm run verify:production`. The Chrome checks use Playwright's `channel: 'chrome'`, so Google Chrome must be installed.

See [Development](docs/DEVELOPMENT.md) for optional environment variables, asset tooling and `pnpm run audit:oss`, which checks for accidental private files and credential patterns. `.env.example` is a reference template; startup scripts do not load it automatically.

Runtime models, images and audio are in `public/`; build and test inputs are in `assets/`. Some optional production scripts need additional source material. Tests requiring unavailable material skip automatically.

### Folders

| Folder            | Contents                                                                              |
| ----------------- | ------------------------------------------------------------------------------------- |
| `src/`            | Browser-side UI, input, saving and Three.js rendering (TypeScript)                    |
| `shared/`         | Game rules, movement, collision, world data and characters                            |
| `application/`    | Rooms and sessions, arbitration of actions, and assembling the data sent and received |
| `infrastructure/` | Static serving for Node, and the browser Worker for solo play                         |
| `cloudflare/`     | For the public site (Cloudflare Workers)                                              |
| `public/`         | HTML, 3D models, audio and images that are served                                     |
| `assets/`         | Adoption records that the public build and the tests read                             |
| `scripts/`        | Build, verification and production scripts                                            |
| `tests/`          | Automated tests (`node:test`)                                                         |
| `docs/` | Game specifications, development and architecture |

### Documents

Most documents are written in Japanese.

- [Game specification and controls](docs/game-spec.md)
- [Release notes](docs/releases.md)
- [Document index](docs/README.md)
- [Code structure and dependency boundaries](docs/ARCHITECTURE.md)
- [Public site procedures](docs/CLOUDFLARE_DEPLOYMENT.md)

### Credits and license

Created by Yuri Nakanishi.

The program, 3D models, images, audio and documents are provided under the [Apache License 2.0](LICENSE). Character and mural materials outside its scope are listed in [NOTICE](NOTICE). The game's name and logo are also excluded.

Some 3D models are also published on Meshmell under CC BY 4.0. Terms for external libraries, data and audio sources are listed in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

Bug reports and suggestions are welcome as issues. Pull requests are very welcome (see "Build it with us" above and [CONTRIBUTING.md](CONTRIBUTING.md)). Please report security problems as described in [SECURITY.md](SECURITY.md), not in a public issue. When you take part, please follow the [Code of conduct](CODE_OF_CONDUCT.md).
