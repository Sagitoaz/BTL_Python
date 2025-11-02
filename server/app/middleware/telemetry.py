"""
Telemetry middleware for collecting user coding data.
Stores completion requests/responses for dataset creation and fine-tuning.
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional
import hashlib

logger = logging.getLogger(__name__)


class TelemetryCollector:
    """Collect and store telemetry data for analysis and fine-tuning"""
    
    def __init__(self, data_dir: str = "data/telemetry"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.current_file = self._get_current_file()
    
    def _get_current_file(self) -> Path:
        """Get current day's telemetry file"""
        date_str = datetime.now().strftime("%Y%m%d")
        return self.data_dir / f"telemetry_{date_str}.jsonl"
    
    def _anonymize_user(self, prefix: str, suffix: str) -> str:
        """Create anonymous user ID from code patterns"""
        # Hash the code to create anonymous ID
        content = prefix + suffix
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def record_completion(
        self,
        request_id: str,
        prefix: str,
        suffix: str,
        language: str,
        completion: str,
        latency_ms: float,
        model: str,
        accepted: Optional[bool] = None
    ):
        """
        Record a completion event.
        
        Args:
            request_id: Unique request ID
            prefix: Code before cursor
            suffix: Code after cursor
            language: Programming language
            completion: Generated completion
            latency_ms: Response time in milliseconds
            model: Model used
            accepted: Whether user accepted the suggestion (if known)
        """
        try:
            record = {
                "timestamp": datetime.now().isoformat(),
                "request_id": request_id,
                "user_id": self._anonymize_user(prefix, suffix),
                "language": language,
                "prefix": prefix,
                "suffix": suffix,
                "completion": completion,
                "latency_ms": latency_ms,
                "model": model,
                "accepted": accepted,
                "prefix_length": len(prefix),
                "suffix_length": len(suffix),
                "completion_length": len(completion),
                "completion_lines": completion.count('\n') + 1
            }
            
            # Append to JSONL file
            with open(self.current_file, 'a') as f:
                f.write(json.dumps(record) + '\n')
            
            logger.debug(f"Recorded telemetry: {request_id}")
            
        except Exception as e:
            logger.error(f"Failed to record telemetry: {e}")
    
    def get_stats(self) -> dict:
        """Get statistics from collected data"""
        try:
            total_records = 0
            languages = {}
            total_latency = 0
            
            # Read all telemetry files
            for file in self.data_dir.glob("telemetry_*.jsonl"):
                with open(file, 'r') as f:
                    for line in f:
                        try:
                            record = json.loads(line)
                            total_records += 1
                            lang = record.get("language", "unknown")
                            languages[lang] = languages.get(lang, 0) + 1
                            total_latency += record.get("latency_ms", 0)
                        except:
                            continue
            
            return {
                "total_completions": total_records,
                "languages": languages,
                "avg_latency_ms": total_latency / total_records if total_records > 0 else 0,
                "data_files": len(list(self.data_dir.glob("telemetry_*.jsonl")))
            }
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {}
    
    def export_training_data(self, output_file: str, format: str = "jsonl"):
        """
        Export collected data in format suitable for fine-tuning.
        
        Args:
            output_file: Path to output file
            format: Export format ("jsonl", "csv", "parquet")
        """
        try:
            records = []
            
            # Read all telemetry files
            for file in self.data_dir.glob("telemetry_*.jsonl"):
                with open(file, 'r') as f:
                    for line in f:
                        try:
                            record = json.loads(line)
                            # Convert to training format
                            training_record = {
                                "prompt": f"<prefix>\n{record['prefix']}\n</prefix>\n\n<suffix>\n{record['suffix']}\n</suffix>\n\n<cursor/>\n\nOUTPUT:",
                                "completion": record['completion'],
                                "language": record['language']
                            }
                            records.append(training_record)
                        except:
                            continue
            
            # Export based on format
            if format == "jsonl":
                with open(output_file, 'w') as f:
                    for rec in records:
                        f.write(json.dumps(rec) + '\n')
            elif format == "csv":
                import csv
                with open(output_file, 'w', newline='') as f:
                    if records:
                        writer = csv.DictWriter(f, fieldnames=records[0].keys())
                        writer.writeheader()
                        writer.writerows(records)
            
            logger.info(f"Exported {len(records)} records to {output_file}")
            return len(records)
            
        except Exception as e:
            logger.error(f"Failed to export training data: {e}")
            return 0


# Global telemetry collector instance
_collector: Optional[TelemetryCollector] = None


def get_telemetry_collector() -> TelemetryCollector:
    """Get or create telemetry collector instance"""
    global _collector
    if _collector is None:
        _collector = TelemetryCollector()
    return _collector
