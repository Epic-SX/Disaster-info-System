#!/usr/bin/env python3
"""
P2P地震情報 API v2 Service
Integrates with P2P地震情報 JSON API (v2) and WebSocket API according to specification.yaml
Provides real-time earthquake, tsunami, and emergency alert information.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Union
from enum import Enum
import aiohttp
import websockets
from pydantic import BaseModel, Field, field_validator
from dataclasses import dataclass

# Configure logging
logger = logging.getLogger(__name__)

# API Endpoints according to specification
P2P_API_BASE_URL = "https://api.p2pquake.net/v2"
P2P_WS_URL = "wss://api.p2pquake.net/v2/ws"
P2P_SANDBOX_BASE_URL = "https://api-v2-sandbox.p2pquake.net/v2"
P2P_SANDBOX_WS_URL = "wss://api-realtime-sandbox.p2pquake.net/v2/ws"

class P2PQuakeType(Enum):
    """地震情報の種類"""
    SCALE_PROMPT = "ScalePrompt"  # 震度速報
    DESTINATION = "Destination"  # 震源に関する情報
    SCALE_AND_DESTINATION = "ScaleAndDestination"  # 震度・震源に関する情報
    DETAIL_SCALE = "DetailScale"  # 各地の震度に関する情報
    FOREIGN = "Foreign"  # 遠地地震に関する情報
    OTHER = "Other"  # その他の情報

class ScaleIntensity(Enum):
    """震度レベル"""
    UNKNOWN = -1  # 震度情報なし
    SCALE_1 = 10  # 震度1
    SCALE_2 = 20  # 震度2
    SCALE_3 = 30  # 震度3
    SCALE_4 = 40  # 震度4
    SCALE_5_WEAK = 45  # 震度5弱
    SCALE_5_WEAK_ESTIMATED = 46  # 震度5弱以上と推定されるが震度情報を入手していない
    SCALE_5_STRONG = 50  # 震度5強
    SCALE_6_WEAK = 55  # 震度6弱
    SCALE_6_STRONG = 60  # 震度6強
    SCALE_7 = 70  # 震度7

class TsunamiGrade(Enum):
    """津波予報の種類"""
    MAJOR_WARNING = "MajorWarning"  # 大津波警報
    WARNING = "Warning"  # 津波警報
    WATCH = "Watch"  # 津波注意報
    UNKNOWN = "Unknown"  # 不明

class InformationCode(Enum):
    """情報コード"""
    JMA_QUAKE = 551  # 地震情報
    JMA_TSUNAMI = 552  # 津波予報
    EEW_DETECTION = 554  # 緊急地震速報 発表検出
    AREA_PEERS = 555  # 各地域ピア数
    EEW = 556  # 緊急地震速報（警報）
    USER_QUAKE = 561  # 地震感知情報
    USER_QUAKE_EVALUATION = 9611  # 地震感知情報 解析結果

# Pydantic Models based on specification

class BasicData(BaseModel):
    """基本データ構造"""
    id: Optional[str] = Field(None, description="情報を一意に識別するID")
    code: int = Field(..., description="情報コード")
    time: str = Field(..., description="受信日時")
    
    class Config:
        extra = "ignore"  # Ignore extra fields like _id

class HypocenterInfo(BaseModel):
    """震源情報"""
    name: Optional[str] = Field(None, description="名称")
    latitude: Optional[float] = Field(None, description="緯度")
    longitude: Optional[float] = Field(None, description="経度")
    depth: Optional[int] = Field(None, description="深さ(km)")
    magnitude: Optional[float] = Field(None, description="マグニチュード")

class IssueInfo(BaseModel):
    """発表元情報"""
    source: Optional[str] = Field(None, description="発表元")
    time: str = Field(..., description="発表日時")
    type: str = Field(..., description="発表種類")
    correct: Optional[str] = Field(None, description="訂正の有無")

class EarthquakeInfo(BaseModel):
    """地震情報"""
    time: str = Field(..., description="発生日時")
    hypocenter: Optional[HypocenterInfo] = Field(None, description="震源情報")
    maxScale: Optional[int] = Field(None, description="最大震度")
    domesticTsunami: Optional[str] = Field(None, description="国内への津波の有無")
    foreignTsunami: Optional[str] = Field(None, description="海外での津波の有無")

class ObservationPoint(BaseModel):
    """震度観測点"""
    pref: str = Field(..., description="都道府県")
    addr: str = Field(..., description="震度観測点名称")
    isArea: bool = Field(..., description="区域名かどうか")
    scale: int = Field(..., description="震度")

class Comments(BaseModel):
    """付加文"""
    freeFormComment: str = Field("", description="自由付加文")

class JMAQuake(BasicData):
    """地震情報 (code: 551)"""
    issue: IssueInfo = Field(..., description="発表元の情報")
    earthquake: EarthquakeInfo = Field(..., description="地震情報")
    points: Optional[List[ObservationPoint]] = Field([], description="震度観測点の情報")
    comments: Optional[Comments] = Field(None, description="付加文")

class TsunamiFirstHeight(BaseModel):
    """津波到達予想時刻"""
    arrivalTime: Optional[str] = Field(None, description="第1波の到達予想時刻")
    condition: Optional[str] = Field(None, description="到達条件")

class TsunamiMaxHeight(BaseModel):
    """予想される津波の高さ"""
    description: str = Field(..., description="文字列表現")
    value: Optional[float] = Field(None, description="数値表現")

class TsunamiArea(BaseModel):
    """津波予報区域"""
    grade: str = Field(..., description="津波予報の種類")
    immediate: bool = Field(..., description="直ちに津波が来襲すると予想されているかどうか")
    name: str = Field(..., description="津波予報区名")
    firstHeight: Optional[TsunamiFirstHeight] = Field(None, description="津波の到達予想時刻")
    maxHeight: Optional[TsunamiMaxHeight] = Field(None, description="予想される津波の高さ")

class JMATsunami(BasicData):
    """津波予報 (code: 552)"""
    cancelled: bool = Field(..., description="津波予報が解除されたかどうか")
    issue: IssueInfo = Field(..., description="発表元の情報")
    areas: List[TsunamiArea] = Field([], description="津波予報の詳細")

class AreaPeer(BaseModel):
    """地域ピア情報"""
    id: int = Field(..., description="地域コード")
    peer: int = Field(..., description="ピア数")

class Areapeers(BasicData):
    """各地域ピア数 (code: 555)"""
    areas: List[AreaPeer] = Field(..., description="ピアの地域分布")

class EEWDetection(BasicData):
    """緊急地震速報 発表検出 (code: 554)"""
    type: str = Field(..., description="検出種類")

class EEWHypocenter(BaseModel):
    """緊急地震速報 震源情報"""
    name: Optional[str] = Field(None, description="震央地名")
    reduceName: Optional[str] = Field(None, description="短縮用震央地名")
    latitude: Optional[float] = Field(None, description="緯度")
    longitude: Optional[float] = Field(None, description="経度")
    depth: Optional[float] = Field(None, description="深さ(km)")
    magnitude: Optional[float] = Field(None, description="マグニチュード")

class EEWEarthquake(BaseModel):
    """緊急地震速報 地震情報"""
    originTime: str = Field(..., description="地震発生時刻")
    arrivalTime: str = Field(..., description="地震発現時刻")
    condition: Optional[str] = Field(None, description="仮定震源要素")
    hypocenter: EEWHypocenter = Field(..., description="地震の位置要素")

class EEWIssue(BaseModel):
    """緊急地震速報 発表情報"""
    time: str = Field(..., description="発表時刻")
    eventId: str = Field(..., description="識別情報")
    serial: str = Field(..., description="情報番号")

class EEWArea(BaseModel):
    """緊急地震速報 細分区域"""
    pref: str = Field(..., description="府県予報区")
    name: str = Field(..., description="地域名（細分区域名）")
    scaleFrom: float = Field(..., description="最大予測震度の下限")
    scaleTo: float = Field(..., description="最大予測震度の上限")
    kindCode: Optional[str] = Field(None, description="警報コード")
    arrivalTime: Optional[str] = Field(None, description="主要動の到達予測時刻")

class EEW(BasicData):
    """緊急地震速報（警報） (code: 556)"""
    test: Optional[bool] = Field(False, description="テストかどうか")
    earthquake: Optional[EEWEarthquake] = Field(None, description="地震の情報")
    issue: EEWIssue = Field(..., description="発表情報")
    cancelled: bool = Field(..., description="取消")
    areas: Optional[List[EEWArea]] = Field([], description="細分区域")

class Userquake(BasicData):
    """地震感知情報 (code: 561)"""
    area: int = Field(..., description="地域コード")

class AreaConfidence(BaseModel):
    """地域ごとの信頼度情報"""
    confidence: float = Field(..., description="信頼度（0～1）")
    count: int = Field(..., description="件数")
    display: Optional[str] = Field(None, description="信頼度表示")

class UserquakeEvaluation(BasicData):
    """地震感知情報 解析結果 (code: 9611)"""
    count: int = Field(..., description="件数")
    confidence: float = Field(..., description="信頼度（0～1）")
    started_at: Optional[str] = Field(None, description="開始日時")
    updated_at: Optional[str] = Field(None, description="更新日時")
    area_confidences: Optional[Dict[str, AreaConfidence]] = Field({}, description="地域ごとの信頼度情報")

# Union type for all P2P earthquake information
P2PEarthquakeInfo = Union[JMAQuake, JMATsunami, Areapeers, EEWDetection, EEW, Userquake, UserquakeEvaluation]

@dataclass
class P2PAPIConfig:
    """P2P地震情報 API設定"""
    use_sandbox: bool = False
    enable_websocket: bool = True
    websocket_reconnect_interval: int = 30
    api_timeout: int = 10
    rate_limit_delay: float = 1.0  # 60 requests/minute = 1 request/second

class P2PEarthquakeService:
    """P2P地震情報 API v2 サービス"""
    
    def __init__(self, config: Optional[P2PAPIConfig] = None):
        self.config = config or P2PAPIConfig()
        self.base_url = P2P_SANDBOX_BASE_URL if self.config.use_sandbox else P2P_API_BASE_URL
        self.ws_url = P2P_SANDBOX_WS_URL if self.config.use_sandbox else P2P_WS_URL
        self.session: Optional[aiohttp.ClientSession] = None
        self.ws_connection: Optional[websockets.WebSocketServerProtocol] = None
        self.is_monitoring = False
        self.last_request_time = 0.0
        
        # Data storage
        self.latest_data: Dict[int, Any] = {}  # Store latest data by information code
        self.data_history: List[P2PEarthquakeInfo] = []
        
        # Event callbacks
        self.callbacks: Dict[int, List[callable]] = {}
        
        logger.info(f"P2P地震情報サービス初期化 - {'サンドボックス' if self.config.use_sandbox else '本番環境'}")

    async def __aenter__(self):
        """Async context manager entry"""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.cleanup()

    async def initialize(self):
        """サービス初期化"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.config.api_timeout)
        )
        logger.info("P2P地震情報サービス初期化完了")

    async def cleanup(self):
        """リソースクリーンアップ"""
        self.is_monitoring = False
        
        if self.ws_connection:
            await self.ws_connection.close()
            self.ws_connection = None
            
        if self.session:
            await self.session.close()
            self.session = None
            
        logger.info("P2P地震情報サービスクリーンアップ完了")

    async def _rate_limit(self):
        """レート制限実装"""
        current_time = asyncio.get_event_loop().time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.config.rate_limit_delay:
            wait_time = self.config.rate_limit_delay - time_since_last
            await asyncio.sleep(wait_time)
        
        self.last_request_time = asyncio.get_event_loop().time()

    def register_callback(self, information_code: int, callback: callable):
        """特定の情報コードに対するコールバック登録"""
        if information_code not in self.callbacks:
            self.callbacks[information_code] = []
        self.callbacks[information_code].append(callback)
        logger.info(f"コールバック登録: 情報コード {information_code}")

    async def _trigger_callbacks(self, data: P2PEarthquakeInfo):
        """コールバック実行"""
        if data.code in self.callbacks:
            for callback in self.callbacks[data.code]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(data)
                    else:
                        callback(data)
                except Exception as e:
                    logger.error(f"コールバック実行エラー: {e}")

    def _parse_response_data(self, raw_data: Dict[str, Any]) -> Optional[P2PEarthquakeInfo]:
        """APIレスポンスデータをパース"""
        try:
            code = raw_data.get('code')
            
            if code == InformationCode.JMA_QUAKE.value:
                return JMAQuake(**raw_data)
            elif code == InformationCode.JMA_TSUNAMI.value:
                return JMATsunami(**raw_data)
            elif code == InformationCode.AREA_PEERS.value:
                return Areapeers(**raw_data)
            elif code == InformationCode.EEW_DETECTION.value:
                return EEWDetection(**raw_data)
            elif code == InformationCode.EEW.value:
                return EEW(**raw_data)
            elif code == InformationCode.USER_QUAKE.value:
                return Userquake(**raw_data)
            elif code == InformationCode.USER_QUAKE_EVALUATION.value:
                return UserquakeEvaluation(**raw_data)
            else:
                logger.warning(f"未知の情報コード: {code}")
                return None
                
        except Exception as e:
            logger.error(f"データパースエラー: {e}")
            return None

    async def get_history(
        self, 
        codes: Optional[List[int]] = None,
        limit: int = 10,
        offset: int = 0
    ) -> List[P2PEarthquakeInfo]:
        """履歴データ取得 (GET /history)"""
        if not self.session:
            await self.initialize()
        
        await self._rate_limit()
        
        params = {
            'limit': min(max(limit, 1), 100),  # 1-100の範囲
            'offset': max(offset, 0)
        }
        
        if codes:
            params['codes'] = codes
        
        try:
            url = f"{self.base_url}/history"
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    result = []
                    
                    for item in data:
                        parsed = self._parse_response_data(item)
                        if parsed:
                            result.append(parsed)
                    
                    logger.info(f"履歴データ取得成功: {len(result)}件")
                    return result
                else:
                    logger.error(f"履歴データ取得失敗: HTTP {response.status}")
                    return []
                    
        except Exception as e:
            logger.error(f"履歴データ取得エラー: {e}")
            return []

    async def get_jma_quakes(
        self,
        limit: int = 10,
        offset: int = 0,
        order: int = -1,
        since_date: Optional[str] = None,
        until_date: Optional[str] = None,
        quake_type: Optional[str] = None,
        min_magnitude: Optional[float] = None,
        max_magnitude: Optional[float] = None,
        min_scale: Optional[int] = None,
        max_scale: Optional[int] = None
    ) -> List[JMAQuake]:
        """JMA地震情報リスト取得 (GET /jma/quake)"""
        if not self.session:
            await self.initialize()
        
        await self._rate_limit()
        
        params = {
            'limit': min(max(limit, 1), 100),
            'offset': max(offset, 0),
            'order': order
        }
        
        # Optional parameters
        if since_date:
            params['since_date'] = since_date
        if until_date:
            params['until_date'] = until_date
        if quake_type:
            params['quake_type'] = quake_type
        if min_magnitude is not None:
            params['min_magnitude'] = min_magnitude
        if max_magnitude is not None:
            params['max_magnitude'] = max_magnitude
        if min_scale is not None:
            params['min_scale'] = min_scale
        if max_scale is not None:
            params['max_scale'] = max_scale
        
        try:
            url = f"{self.base_url}/jma/quake"
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    result = []
                    
                    for item in data:
                        try:
                            quake = JMAQuake(**item)
                            result.append(quake)
                        except Exception as e:
                            logger.error(f"地震情報パースエラー: {e}")
                    
                    logger.info(f"JMA地震情報取得成功: {len(result)}件")
                    return result
                else:
                    logger.error(f"JMA地震情報取得失敗: HTTP {response.status}")
                    return []
                    
        except Exception as e:
            logger.error(f"JMA地震情報取得エラー: {e}")
            return []

    async def get_jma_quake_by_id(self, quake_id: str) -> Optional[JMAQuake]:
        """特定の地震情報取得 (GET /jma/quake/{id})"""
        if not self.session:
            await self.initialize()
        
        await self._rate_limit()
        
        try:
            url = f"{self.base_url}/jma/quake/{quake_id}"
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return JMAQuake(**data)
                elif response.status == 404:
                    logger.warning(f"地震情報が見つかりません: {quake_id}")
                    return None
                else:
                    logger.error(f"地震情報取得失敗: HTTP {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"地震情報取得エラー: {e}")
            return None

    async def get_jma_tsunamis(
        self,
        limit: int = 10,
        offset: int = 0,
        order: int = -1,
        since_date: Optional[str] = None,
        until_date: Optional[str] = None
    ) -> List[JMATsunami]:
        """JMA津波予報リスト取得 (GET /jma/tsunami)"""
        if not self.session:
            await self.initialize()
        
        await self._rate_limit()
        
        params = {
            'limit': min(max(limit, 1), 100),
            'offset': max(offset, 0),
            'order': order
        }
        
        if since_date:
            params['since_date'] = since_date
        if until_date:
            params['until_date'] = until_date
        
        try:
            url = f"{self.base_url}/jma/tsunami"
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    result = []
                    
                    for item in data:
                        try:
                            tsunami = JMATsunami(**item)
                            result.append(tsunami)
                        except Exception as e:
                            logger.error(f"津波予報パースエラー: {e}")
                    
                    logger.info(f"JMA津波予報取得成功: {len(result)}件")
                    return result
                else:
                    logger.error(f"JMA津波予報取得失敗: HTTP {response.status}")
                    return []
                    
        except Exception as e:
            logger.error(f"JMA津波予報取得エラー: {e}")
            return []

    async def get_jma_tsunami_by_id(self, tsunami_id: str) -> Optional[JMATsunami]:
        """特定の津波予報取得 (GET /jma/tsunami/{id})"""
        if not self.session:
            await self.initialize()
        
        await self._rate_limit()
        
        try:
            url = f"{self.base_url}/jma/tsunami/{tsunami_id}"
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return JMATsunami(**data)
                elif response.status == 404:
                    logger.warning(f"津波予報が見つかりません: {tsunami_id}")
                    return None
                else:
                    logger.error(f"津波予報取得失敗: HTTP {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"津波予報取得エラー: {e}")
            return None

    async def start_websocket_monitoring(self):
        """WebSocket監視開始"""
        if not self.config.enable_websocket:
            logger.warning("WebSocket監視が無効です")
            return
        
        self.is_monitoring = True
        logger.info("WebSocket監視開始")
        
        while self.is_monitoring:
            try:
                async with websockets.connect(self.ws_url) as websocket:
                    self.ws_connection = websocket
                    logger.info(f"WebSocket接続成功: {self.ws_url}")
                    
                    async for message in websocket:
                        if not self.is_monitoring:
                            break
                            
                        try:
                            data = json.loads(message)
                            parsed = self._parse_response_data(data)
                            
                            if parsed:
                                # Update latest data
                                self.latest_data[parsed.code] = parsed
                                
                                # Add to history (keep last 1000 items)
                                self.data_history.append(parsed)
                                if len(self.data_history) > 1000:
                                    self.data_history = self.data_history[-1000:]
                                
                                # Trigger callbacks
                                await self._trigger_callbacks(parsed)
                                
                                logger.info(f"WebSocketデータ受信: コード {parsed.code}, ID {parsed.id}")
                            
                        except json.JSONDecodeError as e:
                            logger.error(f"WebSocketメッセージパースエラー: {e}")
                        except Exception as e:
                            logger.error(f"WebSocketメッセージ処理エラー: {e}")
                            
            except websockets.exceptions.ConnectionClosed:
                logger.warning("WebSocket接続が閉じられました")
            except Exception as e:
                logger.error(f"WebSocket接続エラー: {e}")
            
            if self.is_monitoring:
                logger.info(f"WebSocket再接続まで {self.config.websocket_reconnect_interval}秒待機")
                await asyncio.sleep(self.config.websocket_reconnect_interval)
        
        logger.info("WebSocket監視終了")

    def stop_websocket_monitoring(self):
        """WebSocket監視停止"""
        self.is_monitoring = False
        logger.info("WebSocket監視停止要求")

    def get_latest_earthquakes(self, limit: int = 10) -> List[JMAQuake]:
        """最新の地震情報取得"""
        earthquakes = [
            data for data in self.data_history 
            if isinstance(data, JMAQuake)
        ]
        return earthquakes[-limit:] if earthquakes else []

    def get_latest_tsunamis(self, limit: int = 10) -> List[JMATsunami]:
        """最新の津波予報取得"""
        tsunamis = [
            data for data in self.data_history 
            if isinstance(data, JMATsunami)
        ]
        return tsunamis[-limit:] if tsunamis else []

    def get_latest_eew(self, limit: int = 10) -> List[EEW]:
        """最新の緊急地震速報取得"""
        eews = [
            data for data in self.data_history 
            if isinstance(data, EEW)
        ]
        return eews[-limit:] if eews else []

    def get_service_status(self) -> Dict[str, Any]:
        """サービス状態取得"""
        return {
            'is_monitoring': self.is_monitoring,
            'websocket_connected': self.ws_connection is not None,
            'use_sandbox': self.config.use_sandbox,
            'base_url': self.base_url,
            'ws_url': self.ws_url,
            'latest_data_count': len(self.latest_data),
            'history_count': len(self.data_history),
            'registered_callbacks': sum(len(callbacks) for callbacks in self.callbacks.values())
        }

# Utility functions for scale conversion
def scale_int_to_string(scale_int: int) -> str:
    """震度整数値を文字列に変換"""
    scale_map = {
        10: "1", 20: "2", 30: "3", 40: "4",
        45: "5弱", 46: "5弱*", 50: "5強",
        55: "6弱", 60: "6強", 70: "7"
    }
    return scale_map.get(scale_int, "不明")

def parse_p2p_time(time_str: str) -> datetime:
    """P2P地震情報の時刻文字列をdatetimeオブジェクトに変換"""
    try:
        # Format: "2006/01/02 15:04:05.999"
        return datetime.strptime(time_str, "%Y/%m/%d %H:%M:%S.%f")
    except ValueError:
        try:
            # Format without milliseconds: "2006/01/02 15:04:05"
            return datetime.strptime(time_str, "%Y/%m/%d %H:%M:%S")
        except ValueError:
            logger.error(f"時刻パースエラー: {time_str}")
            return datetime.now()

# Example usage and testing
async def main():
    """テスト用メイン関数"""
    config = P2PAPIConfig(use_sandbox=True, enable_websocket=True)
    
    async with P2PEarthquakeService(config) as service:
        # Register callbacks
        def on_earthquake(data: JMAQuake):
            print(f"地震情報受信: {data.earthquake.hypocenter.name if data.earthquake.hypocenter else '不明'} M{data.earthquake.hypocenter.magnitude if data.earthquake.hypocenter else '不明'}")
        
        def on_tsunami(data: JMATsunami):
            print(f"津波予報受信: {'解除' if data.cancelled else '発表'}")
        
        async def on_eew(data: EEW):
            if not data.cancelled and data.earthquake:
                print(f"緊急地震速報: {data.earthquake.hypocenter.name} M{data.earthquake.hypocenter.magnitude}")
        
        service.register_callback(InformationCode.JMA_QUAKE.value, on_earthquake)
        service.register_callback(InformationCode.JMA_TSUNAMI.value, on_tsunami)
        service.register_callback(InformationCode.EEW.value, on_eew)
        
        # Start WebSocket monitoring
        monitoring_task = asyncio.create_task(service.start_websocket_monitoring())
        
        # Get some historical data
        history = await service.get_history(limit=5)
        print(f"履歴データ: {len(history)}件")
        
        earthquakes = await service.get_jma_quakes(limit=3)
        print(f"地震情報: {len(earthquakes)}件")
        
        # Wait for real-time data
        await asyncio.sleep(60)  # Monitor for 1 minute
        
        service.stop_websocket_monitoring()
        await monitoring_task

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    asyncio.run(main()) 