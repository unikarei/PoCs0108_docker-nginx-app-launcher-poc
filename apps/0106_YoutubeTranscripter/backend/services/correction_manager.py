"""
Correction Result Management
Handles saving, retrieving, and managing correction results
"""
import logging
from typing import Optional, Dict, Any, List
import difflib

from database import SessionLocal
from models import CorrectedTranscript

logger = logging.getLogger(__name__)


class CorrectionManager:
    """
    Service for managing correction results
    """
    
    def __init__(self):
        """Initialize correction manager"""
        self.job_manager = None
        
        # Lazy import to avoid circular dependency
        try:
            from services.job_manager import JobManager
            self.job_manager = JobManager()
        except ImportError:
            logger.warning("JobManager not available")
    
    def _get_db(self):
        """Get database session"""
        return SessionLocal()
    
    def save_correction(
        self,
        job_id: str,
        corrected_text: str,
        original_text: str,
        changes_summary: str,
        model: str
    ) -> bool:
        """
        Save correction result to database
        
        Args:
            job_id: Job identifier
            corrected_text: Corrected text
            original_text: Original transcript text
            changes_summary: Summary of changes
            model: Model used for correction
            
        Returns:
            True if successful, False otherwise
        """
        db = self._get_db()
        try:
            correction = CorrectedTranscript(
                job_id=job_id,
                corrected_text=corrected_text,
                original_text=original_text,
                changes_summary=changes_summary,
                correction_model=model
            )
            
            db.add(correction)
            db.commit()
            
            logger.info(f"Saved correction for job {job_id}")
            
            # Update job status if job manager available
            if self.job_manager:
                self.job_manager.update_job_status(job_id, "corrected")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to save correction: {e}")
            db.rollback()
            return False
            
        finally:
            db.close()
    
    def get_correction(self, job_id: str) -> Optional[CorrectedTranscript]:
        """
        Get correction by job ID
        
        Args:
            job_id: Job identifier
            
        Returns:
            CorrectedTranscript object or None
        """
        db = self._get_db()
        try:
            correction = db.query(CorrectedTranscript).filter(
                CorrectedTranscript.job_id == job_id
            ).first()
            
            return correction
            
        finally:
            db.close()
    
    def list_corrections(self, job_id: str) -> List[CorrectedTranscript]:
        """
        List all corrections for a job
        
        Args:
            job_id: Job identifier
            
        Returns:
            List of CorrectedTranscript objects
        """
        db = self._get_db()
        try:
            corrections = db.query(CorrectedTranscript).filter(
                CorrectedTranscript.job_id == job_id
            ).all()
            
            return corrections
            
        finally:
            db.close()
    
    def prepare_comparison_data(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Prepare data for side-by-side comparison display
        
        Args:
            job_id: Job identifier
            
        Returns:
            Dict with original and corrected texts
        """
        correction = self.get_correction(job_id)
        
        if not correction:
            logger.warning(f"No correction found for job {job_id}")
            return None
        
        return {
            'job_id': job_id,
            'original': correction.original_text,
            'corrected': correction.corrected_text,
            'changes_summary': correction.changes_summary,
            'model': correction.correction_model,
            'created_at': correction.created_at.isoformat() if correction.created_at else None
        }
    
    def calculate_diff(self, original: str, corrected: str) -> Dict[str, Any]:
        """
        Calculate highlighted differences between texts
        
        Args:
            original: Original text
            corrected: Corrected text
            
        Returns:
            Dict with diff data
        """
        # Use difflib to calculate differences
        differ = difflib.Differ()
        diff = list(differ.compare(original.split('\n'), corrected.split('\n')))
        
        additions = []
        deletions = []
        unchanged = []
        
        for line in diff:
            if line.startswith('+ '):
                additions.append(line[2:])
            elif line.startswith('- '):
                deletions.append(line[2:])
            elif line.startswith('  '):
                unchanged.append(line[2:])
        
        return {
            'additions': additions,
            'deletions': deletions,
            'unchanged': unchanged,
            'total_changes': len(additions) + len(deletions)
        }
    
    def accept_correction(self, job_id: str) -> bool:
        """
        Accept correction (mark as final)
        
        Args:
            job_id: Job identifier
            
        Returns:
            True if successful
        """
        try:
            # Update job status to completed
            if self.job_manager:
                self.job_manager.update_job_status(job_id, "completed")
            
            logger.info(f"Accepted correction for job {job_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to accept correction: {e}")
            return False
    
    def reject_correction(self, job_id: str) -> bool:
        """
        Reject correction (revert to original)
        
        Args:
            job_id: Job identifier
            
        Returns:
            True if successful
        """
        db = self._get_db()
        try:
            correction = db.query(CorrectedTranscript).filter(
                CorrectedTranscript.job_id == job_id
            ).first()
            
            if correction:
                db.delete(correction)
                db.commit()
                
                logger.info(f"Rejected and deleted correction for job {job_id}")
                
                # Update job status back to transcribed
                if self.job_manager:
                    self.job_manager.update_job_status(job_id, "transcribed")
                
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to reject correction: {e}")
            db.rollback()
            return False
            
        finally:
            db.close()
    
    def format_for_display(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format comparison data for display
        
        Args:
            data: Raw comparison data
            
        Returns:
            Formatted data ready for display
        """
        # Add formatting for frontend display
        formatted = {
            'original': {
                'text': data.get('original', ''),
                'label': 'Original Transcript'
            },
            'corrected': {
                'text': data.get('corrected', ''),
                'label': 'Corrected Transcript'
            },
            'metadata': {
                'changes': data.get('changes', ''),
                'timestamp': data.get('created_at')
            }
        }
        
        return formatted
    
    def generate_summary(self, original: str, corrected: str) -> str:
        """
        Generate human-readable change summary
        
        Args:
            original: Original text
            corrected: Corrected text
            
        Returns:
            Summary string
        """
        # Calculate character-level changes
        original_len = len(original)
        corrected_len = len(corrected)
        diff_len = abs(corrected_len - original_len)
        
        # Calculate word-level changes
        original_words = original.split()
        corrected_words = corrected.split()
        
        differ = difflib.Differ()
        diff = list(differ.compare(original_words, corrected_words))
        
        additions = sum(1 for d in diff if d.startswith('+ '))
        deletions = sum(1 for d in diff if d.startswith('- '))
        
        if additions == 0 and deletions == 0:
            return "No changes made to the transcript."
        
        summary_parts = []
        
        if additions > 0:
            summary_parts.append(f"{additions} word(s) added")
        
        if deletions > 0:
            summary_parts.append(f"{deletions} word(s) removed")
        
        if diff_len > 0:
            change_type = "longer" if corrected_len > original_len else "shorter"
            summary_parts.append(f"text is {diff_len} character(s) {change_type}")
        
        return ", ".join(summary_parts) + "."
