# 使用GEE下载Sentinel-2卫星影像

# 1 功能说明

使用GEE网页版下载遥感影像通常要去Google云盘里转一下，但是Google云盘又有存储容量限制，除非小氪一手，但我觉得搞定支付渠道已经足够让我激流勇退了，因此可以直接通过GEE提供的Python接口绕开Google网盘，直接从云平台下载到本地计算机。

# 2 需要安装的库

- google-api-python-client
- earthengine-api
- geemap
- geedim（这个一定要安装1.9.0或者1.9.1版本）
- setuptools

```
pip install google-api-python-client==2.169.0
pip install earthengine-api==1.5.13
pip install geemap==0.35.3
pip install geedim==1.9.1
pip install setuptools==69.5.1
```

- 给出了推荐版本，供大家参考，不同库之间的新旧版本可能存在不兼容的情况，非常神奇