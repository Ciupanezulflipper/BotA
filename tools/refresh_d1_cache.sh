#!/data/data/com.termux/files/usr/bin/bash
# Refresh D1 trend cache for all pairs
source /data/data/com.termux/files/home/BotA/.env
source /data/data/com.termux/files/home/BotA/config/strategy.env
export OANDA_API_TOKEN OANDA_API_URL

python3 << 'PYEOF'
import json, urllib.request, datetime, os

TOKEN = os.environ.get('OANDA_API_TOKEN','')
URL = os.environ.get('OANDA_API_URL','https://api-fxpractice.oanda.com')
PAIRS = [('EURUSD','EUR_USD'),('GBPUSD','GBP_USD'),('USDJPY','USD_JPY'),('XAUUSD','XAU_USD')]

for pair, instrument in PAIRS:
    req = urllib.request.Request(
        f"{URL}/v3/instruments/{instrument}/candles?count=50&granularity=D&price=M",
        headers={"Authorization": f"Bearer {TOKEN}"}
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
        candles = [c for c in data['candles'] if c.get('complete',True)]
        closes = [float(c['mid']['c']) for c in candles]
        def ema(v,p):
            k=2.0/(p+1); r=sum(v[:p])/p
            for x in v[p:]: r=x*k+r*(1-k)
            return r
        e9=ema(closes,9); e21=ema(closes,21)
        trend='BUY' if e9>e21 else 'SELL'
        bundle={'pair':pair,'ema9':e9,'ema21':e21,'trend':trend,
                'weak':False,'error':'',
                'updated_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
        path=f"/data/data/com.termux/files/home/BotA/cache/d1_trend_{pair}.json"
        open(path,'w').write(json.dumps(bundle))
        print(f"[D1] {pair}: {trend} EMA9={e9:.5f} EMA21={e21:.5f}")
    except Exception as ex:
        print(f"[D1] {pair} error: {ex}")
PYEOF
