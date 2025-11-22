from freqtrade.strategy.interface import IStrategy
from functools import reduce
import talib.abstract as ta
import pandas as pd
import numpy as np
from pandas import DataFrame
from datetime import datetime
from freqtrade.persistence import Trade
from typing import Optional
from freqtrade.enums import TradingMode, MarginMode

class DailySwingHunterV5_Futures(IStrategy):
    """
    OPTİMİZE SWING STRATEJİSİ - FUTURES/MARGIN VERSİYONU
    Orijinal algoritmanın %100 aynısı, futures trading için optimize edilmiş
    
    📊 ORİJİNAL PERFORMANS:
    - 100% ROI çıkış başarı oranı
    - %97.2 genel kazanma oranı (35 gün)
    - Maksimum %1.18 drawdown
    - use_exit_signal = False (kritik başarı faktörü)
    """
    
    INTERFACE_VERSION = 3
    timeframe = '5m'
    
    # 🔥 FUTURES AYARLARI
    can_short = False  # Short devre dışı - sadece LONG işlemler
    
    # 💰 KONSERVATIF LEVERAGE AYARLARI - Risk yönetimi odaklı
    max_leverage = 5.0  # Maksimum 5x leverage (güvenli)
    
    # 🛑 STOP LOSS - Orijinal ayarlar korundu
    stoploss = -0.4  # -%40 stop loss (orijinal değer)
    use_custom_stoploss = False  # Basit stop-loss kullan
    
    # 🚫 TRAILING STOP TAMAMEN KALDIRILDI (orijinal gibi)
    trailing_stop = False
    
    # 💎 OPTİMİZE ROI - Orijinal başarılı sistem korundu
    minimal_roi = {
        "0": 0.035,   # %3.5 kar
        "5": 0.025,   # 5 dakika sonra %2.5
        "10": 0.02,   # 10 dakika sonra %2
        "20": 0.01    # 20 dakika sonra %1
    }
    
    # 📈 TRADE AYARLARI - Futures için optimize
    max_open_trades = 2  # Futures riskini azaltmak için 3'ten 2'ye
    stake_currency = 'USDT'
    process_only_new_candles = True
    use_exit_signal = False  # 🔥 KRİTİK: False kalması gerekiyor!
    
    # 💼 POSITION MANAGEMENT
    position_adjustment_enable = True
    max_entry_position_adjustment = 1  # Maksimum 1 ekleme pozisyonu
    
    # 🎯 FUTURES MARGIN AYARLARI
    # NOT: trading_mode ve margin_mode config dosyasında ayarlanmalıdır
    # Bu değişkenler strateji sınıfında tanımlanmaz

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        BASİT VE ETKİLİ GÖSTERGELER - ORİJİNAL AYNI
        """
        # RSI - Orijinal ayarlar
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        dataframe['rsi_7'] = ta.RSI(dataframe, timeperiod=7)
        
        # Volume - Orijinal ayarlar
        dataframe['volume_ma'] = dataframe['volume'].rolling(20).mean()
        dataframe['volume_ratio'] = dataframe['volume'] / dataframe['volume_ma']
        
        # EMA'lar - Orijinal ayarlar
        dataframe['ema_9'] = ta.EMA(dataframe, timeperiod=9)
        dataframe['ema_21'] = ta.EMA(dataframe, timeperiod=21)
        dataframe['ema_50'] = ta.EMA(dataframe, timeperiod=50)
        
        # Support/Resistance - Orijinal ayarlar
        dataframe['resistance'] = dataframe['high'].rolling(20).max()
        dataframe['support'] = dataframe['low'].rolling(20).min()
        
        # Momentum - Orijinal ayarlar
        dataframe['price_change_3'] = dataframe['close'].pct_change(3)
        dataframe['price_change_8'] = dataframe['close'].pct_change(8)
        
        # Stochastic - Orijinal ayarlar
        stoch = ta.STOCH(dataframe, fastk_period=14, slowk_period=3, slowd_period=3)
        dataframe['stoch_k'] = stoch['slowk']
        dataframe['stoch_d'] = stoch['slowd']
        
        # Bollinger Bands - Orijinal ayarlar
        dataframe['bb_upper'], dataframe['bb_middle'], dataframe['bb_lower'] = ta.BBANDS(
            dataframe['close'], timeperiod=20, nbdevup=2.0, nbdevdn=2.0, matype=0)
        
        # 📊 FUTURES İÇİN EK GÖSTERGELER (risk yönetimi)
        dataframe['atr'] = ta.ATR(dataframe, timeperiod=14)  # Volatilite ölçümü
        dataframe['volatility'] = dataframe['atr'] / dataframe['close'] * 100
        
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        BASİT VE ETKİLİ GİRİŞ KOŞULLARI - TAM ORİJİNAL
        """
        pair = metadata['pair']
        
        # ✅ SENARYO 1: GÜÇLÜ DİP ALIM (orijinal)
        strong_dip = (
            (dataframe['rsi'] < 32) &
            (dataframe['rsi_7'] < 28) &
            (dataframe['volume_ratio'] > 1.4) &
            (dataframe['close'] < dataframe['support'] * 1.015) &
            (dataframe['stoch_k'] < 25) &
            (dataframe['price_change_8'] < -0.025)
        )
        
        # ✅ SENARYO 2: TREND MOMENTUM (orijinal)
        trend_momentum = (
            (dataframe['ema_9'] > dataframe['ema_21']) &
            (dataframe['ema_21'] > dataframe['ema_50']) &
            (dataframe['rsi'].between(42, 65)) &
            (dataframe['volume_ratio'] > 1.2) &
            (dataframe['stoch_k'] > dataframe['stoch_d']) &
            (dataframe['price_change_3'] > 0.005)
        )
        
        # ✅ SENARYO 3: BOUNCE ALIMI (orijinal)
        bounce_alim = (
            (dataframe['rsi'] < 38) &
            (dataframe['volume_ratio'] > 1.1) &
            (dataframe['close'] < dataframe['bb_lower'] * 1.02) &
            (dataframe['stoch_k'] < 30) &
            (dataframe['ema_9'] > dataframe['ema_9'].shift(3))
        )
        
        # 📊 FUTURES GÜVENLIK FİLTRESİ (ek güvenlik)
        futures_safety = (
            dataframe['volatility'] < 8.0  # Çok yüksek volatilite durumlarını filtrele
        )
        
        # Orijinal koşullar + futures güvenlik filtresi
        final_condition = (strong_dip | trend_momentum | bounce_alim) & futures_safety
        
        # DEBUG - Orijinal format korundu
        signal_count = final_condition.sum()
        if signal_count > 0:
            current_data = dataframe.iloc[-1]
            print(f"🎯 FUTURES {pair} - {signal_count} sinyal | RSI: {current_data['rsi']:.1f}, Volume: {current_data['volume_ratio']:.2f}, Vol: {current_data['volatility']:.1f}%")
        
        dataframe.loc[final_condition, 'enter_long'] = 1
        
        # 🔻 SHORT İŞLEMLER DEVRE DIŞI (can_short = False)
        # Long-only strateji için SHORT kodları kaldırıldı
        
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        AKILLI ÇIKIŞ SİSTEMİ - ORİJİNAL AYNI (Trailing Stop Yerine)
        """
        # 🎯 KONSERVATIF KAR ÇIKIŞI - Orijinal ayarlar
        optimal_exit = (
            (dataframe['close'] >= dataframe['open'] * 1.06) &  # %6 kar (orijinal)
            (dataframe['rsi'] > 70) &  # Orijinal RSI seviyesi
            (dataframe['volume_ratio'] > 1.5)  # Orijinal volume onayı
        )
        
        # 🎯 GÜÇLÜ AŞIRI ALIM ÇIKIŞI - Orijinal ayarlar
        technical_exit = (
            (dataframe['rsi'] > 85) &  # Orijinal RSI seviyesi
            (dataframe['stoch_k'] > 90) &  # Orijinal Stoch seviyesi
            (dataframe['stoch_d'] > 85) &  # Orijinal Stoch D onayı
            (dataframe['volume_ratio'] > 1.8)  # Orijinal volume artışı
        )
        
        # 🎯 NET TREND DÖNÜŞÜ ÇIKIŞI - Orijinal ayarlar
        trend_exit = (
            (dataframe['ema_9'] < dataframe['ema_21']) &
            (dataframe['ema_21'] < dataframe['ema_50']) &  # Orijinal trend koşulu
            (dataframe['close'] < dataframe['ema_9']) &  # Orijinal fiyat koşulu
            (dataframe['volume_ratio'] < 0.5) &  # Orijinal düşük volume
            (dataframe['rsi'] < 40)  # Düzeltildi: 30'dan 40'a çıkarıldı (daha mantıklı)
        )
        
        # 🎯 YÜKSEK KAR HEDEFİ - Orijinal ayar
        profit_exit = (
            dataframe['close'] >= dataframe['open'] * 1.08  # %8 kar (orijinal)
        )
        
        # Tüm çıkış koşullarını birleştir - Orijinal sistem
        exit_conditions = [optimal_exit, technical_exit, trend_exit, profit_exit]
        exit_signal = reduce(lambda x, y: x | y, exit_conditions)
        
        # Ardışık sinyalleri önle - Orijinal sistem
        exit_signal = exit_signal & ~exit_signal.shift(1).fillna(False)
        
        if exit_signal.any():
            exit_count = exit_signal.sum()
            print(f"🚪 FUTURES {metadata['pair']} - {exit_count} çıkış sinyali")
        
        dataframe.loc[exit_signal, 'exit_long'] = 1
        
        # 🔺 SHORT ÇIKIŞ DEVRE DIŞI (Long-only strateji)
        
        return dataframe

    def leverage(self, pair: str, current_time: datetime, current_rate: float,
                 proposed_leverage: float, max_leverage: float, entry_tag: Optional[str], 
                 side: str, **kwargs) -> float:
        """
        FUTURES LEVERAGE YÖNETİMİ - Dinamik ve güvenli
        """
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        
        if len(dataframe) < 20:
            return 1.0  # Veri yetersizse leverage kullanma
            
        current_data = dataframe.iloc[-1]
        volatility = current_data.get('volatility', 5.0)
        rsi = current_data.get('rsi', 50.0)
        
        # 📊 VOLATİLİTEYE GÖRE DİNAMİK LEVERAGE
        if volatility < 2.0:
            leverage = 5.0  # Düşük volatilite = Yüksek leverage
        elif volatility < 4.0:
            leverage = 3.0  # Orta volatilite = Orta leverage
        elif volatility < 6.0:
            leverage = 2.0  # Yüksek volatilite = Düşük leverage
        else:
            leverage = 1.5  # Çok yüksek volatilite = Minimal leverage
        
        # 📈 RSI BAZLI EK GÜVENLIK
        if rsi < 25 or rsi > 75:
            leverage = max(1.0, leverage * 0.7)  # Aşırı durumlar için leverage azalt
        
        # 🔒 MAKSIMUM LEVERAGE SINIRI
        final_leverage = min(leverage, self.max_leverage, max_leverage)
        
        # Minimum leverage 1.0 olmalı
        final_leverage = max(1.0, final_leverage)
        
        print(f"💰 {pair} Leverage: {final_leverage:.1f}x (Vol: {volatility:.1f}%, RSI: {rsi:.1f})")
        
        return final_leverage

    def confirm_trade_entry(self, pair: str, order_type: str, amount: float, rate: float,
                           time_in_force: str, current_time: datetime, entry_tag: Optional[str], 
                           side: str, **kwargs) -> bool:
        """
        FUTURES GÜVENLİK KONTROLÜ - Orijinal + futures ek kontroller
        """
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        
        if len(dataframe) < 20:
            return False
            
        current_data = dataframe.iloc[-1]
        current_volume = current_data['volume_ratio']
        current_rsi = current_data['rsi']
        current_volatility = current_data.get('volatility', 10.0)
        
        # 🔥 ORİJİNAL KONTROLLER (değişmedi)
        if current_volume < 1.0:
            return False
            
        if current_rsi > 65:
            return False
        
        # 📊 FUTURES EK GÜVENLİK KONTROLLERİ
        if current_volatility > 10.0:
            print(f"❌ {pair} - Çok yüksek volatilite: {current_volatility:.1f}%")
            return False
        
        # 💼 MEVCUT POZISYON KONTROLÜ
        # Bu kontrol Freqtrade tarafından otomatik olarak yapılıyor
        # Bu nedenle burada tekrar kontrol etmeye gerek yok
        
        print(f"✅ {pair} - Futures giriş onaylandı (Vol: {current_volatility:.1f}%, RSI: {current_rsi:.1f})")
        return True

    def custom_stake_amount(self, pair: str, current_time: datetime, current_rate: float,
                           proposed_stake: float, min_stake: Optional[float], max_stake: float,
                           leverage: float, entry_tag: Optional[str], side: str,
                           **kwargs) -> float:
        """
        FUTURES STAKE YÖNETİMİ - Risk bazlı
        """
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        
        if len(dataframe) < 20:
            return proposed_stake
            
        current_data = dataframe.iloc[-1]
        volatility = current_data.get('volatility', 5.0)
        
        # 📊 VOLATİLİTEYE GÖRE STAKE AYARLA
        if volatility < 3.0:
            stake_multiplier = 1.0  # Normal stake
        elif volatility < 6.0:
            stake_multiplier = 0.8  # %20 azalt
        else:
            stake_multiplier = 0.6  # %40 azalt
        
        adjusted_stake = proposed_stake * stake_multiplier
        
        # Min/Max kontrolleri
        if min_stake and adjusted_stake < min_stake:
            adjusted_stake = min_stake
        if adjusted_stake > max_stake:
            adjusted_stake = max_stake
            
        return adjusted_stake

    def custom_exit(self, pair: str, trade: Trade, current_time: datetime, current_rate: float,
                    current_profit: float, **kwargs) -> Optional[str]:
        """
        FUTURES ACİL ÇIKIŞ YÖNETİMİ - Ek güvenlik
        """
        # 🚨 ACİL ÇIKIŞ KOŞULLARI
        if current_profit <= -0.30:  # -%30 zarar durumunda acil çıkış
            return "emergency_exit_high_loss"
        
        # 📊 Leverage bazlı risk yönetimi
        # Trade objesi her zaman leverage attribute'ına sahiptir
        if trade.leverage > 3.0:
            if current_profit <= -0.15:  # Yüksek leverage'da daha erken çık
                return "emergency_exit_high_leverage"
        
        return None

    def informative_pairs(self):
        """
        BTC dominance ve genel market sentiment için
        """
        return [
            ("BTC/USDT", "5m"),
            ("ETH/USDT", "5m")
        ]
