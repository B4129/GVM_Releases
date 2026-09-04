# 動画編集用効果音の合成

2026-09-05追加パックの新作100種類（GVM_011〜GVM_110）を再生成します。
外部の音声サンプルやネットワーク接続を使わず、波形・ノイズ・残響から合成します。
最初の承認済みサンプル10種類（GVM_001〜GVM_010）は、配信済みWAVをそのまま保持しています。

Python 3とNumPyが必要です。作成時のNumPyのバージョンはrequirements.txtに記載しています。

```sh
python -m pip install -r requirements.txt
python render.py --output ./rendered-pack
```

出力先のsfx/に100個のWAV、expansion-manifest.jsonに用途・長さ・ハッシュ・検証値を書き出します。
配信ファイルを直接上書きせず、明示した出力先で確認してから反映してください。
presetごとに固定シードを使用し、別の音の追加が既存のレシピへ影響しない構成です。

形式は48 kHz、24-bit PCM WAV、ステレオ。推定true peakを-6 dBFS以下に調整し、
先頭・末尾、直流成分、モノラル化、重複ハッシュを生成後のPCMで確認します。
