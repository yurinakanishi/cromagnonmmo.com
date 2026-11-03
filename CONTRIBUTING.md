# 参加のしかた / Contributing

このリポジトリを土台にしたゲーム作りや改善を歓迎します。ライセンスは [Apache License 2.0](LICENSE)、対象外の素材は [NOTICE](NOTICE) に記載しています。

- **プルリクエスト**：大歓迎です！特に、新しい機能の追加を待っています。自分のキャラクターを洞窟の壁画に登場させる、プレイヤーとして動かせるようにする、撫でられる仲間のマスコットにするなど、自由なアイデアをぜひ。不具合の修正や改善も受け付けます。
- **PRの言語**：タイトルと本文は日本語と英語を併記してください。タイトルは `日本語 / English` の形式にし、本文は言語ごとに分けて変更内容・理由・検証結果を書いてください。翻訳ツールも利用できます。
- **自分のキャラクターを加えるとき**：通常の投稿はApache-2.0で受け付けます。別の利用条件を希望する場合は、プルリクエストで教えてください。外部素材には出典と利用条件を添えてください。
- **変更の検証**：[開発環境](docs/DEVELOPMENT.md) に従い、`pnpm run audit:oss`・`pnpm run check`・`pnpm run format:check`・`pnpm test` を実行し、未実施やスキップはプルリクエストに記載してください。ログやスクリーンショットを添える前に、保存データ・認証情報・個人情報を取り除いてください。
- **不具合の報告・提案**：Issueで受け付けます。再現の手順、ブラウザーと端末（PC・スマートフォン）、表示されたエラーがあると助かります。
- **セキュリティの問題**：公開のIssueには書かず、[SECURITY.md](SECURITY.md) の方法で知らせてください。
- **行動規範**：参加するときは [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) を守ってください。

---

Building a game on top of this repository and improving it are welcome. The license is [Apache License 2.0](LICENSE), with excluded materials listed in [NOTICE](NOTICE).

- **Pull requests:** very welcome, above all new features! Put your own character in the cave murals, make it playable or a mascot you can pet, or bring your own idea. Fixes and improvements are welcome too.
- **PR language:** include both Japanese and English in the title and description. Use `日本語 / English` for the title, and separate language sections in the description covering the changes, reasons and validation results. You may use translation tools.
- **Adding your own character:** contributions use Apache-2.0 by default. Let us know in the pull request if you want different terms. Include the source and usage terms for external materials.
- **Validation:** follow [Development](docs/DEVELOPMENT.md), run `pnpm run audit:oss`, `pnpm run check`, `pnpm run format:check` and `pnpm test`, and record skipped or unrun checks in the pull request. Remove saves, credentials and personal data from logs and screenshots before attaching them.
- **Bug reports and suggestions:** welcome as issues. Steps to reproduce, the browser and device, and any error shown help a lot.
- **Security problems:** do not open a public issue; follow [SECURITY.md](SECURITY.md).
- **Code of conduct:** please follow [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) when you take part.
