# 動画編集用効果音の合成

2026-09-05追加パックの新作100種類を再生成します。
外部の音声サンプルやネットワーク接続を使わず、波形・ノイズ・残響から合成します。
最初のサンプル10種類は、配信済みWAVをそのまま保持しています。

Python 3とNumPyが必要です。作成時のNumPyのバージョンはrequirements.txtに記載しています。

```sh
python -m pip install -r requirements.txt
python render.py --output ./rendered-pack
```

出力先のsfx/に100個のWAV、expansion-manifest.jsonに用途・長さ・ハッシュ・検証値を書き出します。
配信ファイルを直接上書きせず、明示した出力先で確認してから反映してください。
形式は48 kHz、24-bit PCM WAV、ステレオ。推定true peakを-6 dBFS以下に調整し、
先頭・末尾、直流成分、モノラル化、重複ハッシュを生成後のPCMで確認します。

## 名前と音源の対応

選択画面に表示する名前は「音の特徴（用途）」です。
詳しくは[効果音の命名規則](../../sfx/命名規則.md)を参照してください。
管理番号はsfx-registry.jsonのpresetNumberとpresets.pyのnumberで対応させます。
番号は表示名に含めず、追加時も既存の番号・IDを変更しません。

名前・旧ファイル名・固定シード・公開音源のハッシュは、リポジトリ直下のsfx-registry.jsonで管理します。
シードは文字列として保存し、Pythonで整数に戻します。ファイル名からシードを再計算しないため、
名前を変えても音は変わりません。生成後は公開済み音源のSHA-256との一致も検証します。
別のレジストリを使う場合は`--registry <path>`を明示してください。

カタログを作り直す場合はリポジトリ直下で次を実行します。

```sh
node scripts/generate-sfx-index.js
node --test scripts/generate-sfx-index.test.js
```

旧ファイル名は互換用に保持しますが、カタログには新しい名前だけを載せます。
再生成したsfx-list.jsonに旧名が再登場したり、長さ・サイズ・既存IDが失われたりしない構成です。
