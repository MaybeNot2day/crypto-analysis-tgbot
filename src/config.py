"""
Configuration management for the Crypto Outlier Detection Dashboard.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


@dataclass
class ExchangeConfig:
    """Configuration for an exchange."""
    name: str
    base_url: str
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    rate_limit_per_minute: int = 1200
    enabled: bool = True


@dataclass
class UniverseConfig:
    """Configuration for universe management."""
    top_n: int = 50
    update_frequency_hours: int = 24
    storage_path: str = "data/universe.parquet"


@dataclass
class FactorWeights:
    """Weights for factor computation."""
    momentum: float = 0.25
    mean_reversion: float = 0.25
    carry: float = 0.3
    volume: float = 0.2


@dataclass
class Thresholds:
    """Thresholds for outlier detection."""
    outlier_z_score: float = 2.0
    top_n_outliers: int = 10
    bottom_n_outliers: int = 10
    min_data_points: int = 24  # Minimum data points for factor calculation


@dataclass
class DatabaseConfig:
    """Configuration for data storage."""
    type: str = "duckdb"  # or "timescaledb"
    path: str = "data/crypto_data.duckdb"
    host: Optional[str] = None
    port: Optional[int] = None
    database: Optional[str] = None
    user: Optional[str] = None
    password: Optional[str] = None


@dataclass
class TelegramConfig:
    """Configuration for Telegram bot notifications."""
    enabled: bool = False
    bot_token: Optional[str] = None
    chat_id: Optional[str] = None


@dataclass
class Config:
    """Main configuration class."""
    exchanges: Dict[str, ExchangeConfig] = field(default_factory=dict)
    universe: UniverseConfig = field(default_factory=UniverseConfig)
    factor_weights: FactorWeights = field(default_factory=FactorWeights)
    thresholds: Thresholds = field(default_factory=Thresholds)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    telegram: TelegramConfig = field(default_factory=TelegramConfig)
    pipeline_frequency_minutes: int = 60
    data_retention_days: int = 30

    @classmethod
    def from_yaml(cls, config_path: str) -> "Config":
        """Load configuration from YAML file."""
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(path, "r") as f:
            data = yaml.safe_load(f)

        # Load exchanges
        exchanges = {}
        for name, exchange_data in data.get("exchanges", {}).items():
            exchanges[name] = ExchangeConfig(
                name=name,
                base_url=exchange_data.get("base_url", ""),
                api_key=os.getenv(f"{name.upper()}_API_KEY") or exchange_data.get("api_key"),
                api_secret=os.getenv(f"{name.upper()}_API_SECRET") or exchange_data.get("api_secret"),
                rate_limit_per_minute=exchange_data.get("rate_limit_per_minute", 1200),
                enabled=exchange_data.get("enabled", True),
            )

        # Load universe config
        universe_data = data.get("universe", {})
        universe = UniverseConfig(
            top_n=universe_data.get("top_n", 50),
            update_frequency_hours=universe_data.get("update_frequency_hours", 24),
            storage_path=universe_data.get("storage_path", "data/universe.parquet"),
        )

        # Load factor weights
        weights_data = data.get("factor_weights", {})
        factor_weights = FactorWeights(
            momentum=weights_data.get("momentum", 0.25),
            mean_reversion=weights_data.get("mean_reversion", 0.25),
            carry=weights_data.get("carry", 0.3),
            volume=weights_data.get("volume", 0.2),
        )

        # Load thresholds
        thresholds_data = data.get("thresholds", {})
        thresholds = Thresholds(
            outlier_z_score=thresholds_data.get("outlier_z_score", 2.0),
            top_n_outliers=thresholds_data.get("top_n_outliers", 10),
            bottom_n_outliers=thresholds_data.get("bottom_n_outliers", 10),
            min_data_points=thresholds_data.get("min_data_points", 24),
        )

        # Load database config
        db_data = data.get("database", {})
        database = DatabaseConfig(
            type=db_data.get("type", "duckdb"),
            path=db_data.get("path", "data/crypto_data.duckdb"),
            host=db_data.get("host"),
            port=db_data.get("port"),
            database=db_data.get("database"),
            user=os.getenv("DB_USER") or db_data.get("user"),
            password=os.getenv("DB_PASSWORD") or db_data.get("password"),
        )

        # Load Telegram config
        telegram_data = data.get("telegram", {})
        telegram = TelegramConfig(
            enabled=telegram_data.get("enabled", False),
            bot_token=os.getenv("TELEGRAM_BOT_TOKEN") or telegram_data.get("bot_token"),
            chat_id=os.getenv("TELEGRAM_CHAT_ID") or telegram_data.get("chat_id"),
        )

        return cls(
            exchanges=exchanges,
            universe=universe,
            factor_weights=factor_weights,
            thresholds=thresholds,
            database=database,
            telegram=telegram,
            pipeline_frequency_minutes=data.get("pipeline_frequency_minutes", 60),
            data_retention_days=data.get("data_retention_days", 30),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "exchanges": {
                name: {
                    "base_url": exc.base_url,
                    "rate_limit_per_minute": exc.rate_limit_per_minute,
                    "enabled": exc.enabled,
                }
                for name, exc in self.exchanges.items()
            },
            "universe": {
                "top_n": self.universe.top_n,
                "update_frequency_hours": self.universe.update_frequency_hours,
                "storage_path": self.universe.storage_path,
            },
            "factor_weights": {
                "momentum": self.factor_weights.momentum,
                "mean_reversion": self.factor_weights.mean_reversion,
                "carry": self.factor_weights.carry,
                "volume": self.factor_weights.volume,
            },
            "thresholds": {
                "outlier_z_score": self.thresholds.outlier_z_score,
                "top_n_outliers": self.thresholds.top_n_outliers,
                "bottom_n_outliers": self.thresholds.bottom_n_outliers,
                "min_data_points": self.thresholds.min_data_points,
            },
            "database": {
                "type": self.database.type,
                "path": self.database.path,
            },
            "telegram": {
                "enabled": self.telegram.enabled,
            },
            "pipeline_frequency_minutes": self.pipeline_frequency_minutes,
            "data_retention_days": self.data_retention_days,
        }


def load_config(config_path: Optional[str] = None) -> Config:
    """Load configuration from file or environment."""
    if config_path is None:
        config_path = os.getenv("CONFIG_PATH", "config/config.yaml")

    if Path(config_path).exists():
        return Config.from_yaml(config_path)
    else:
        # Return default config if file doesn't exist
        return Config()

