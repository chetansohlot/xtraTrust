from django.db import models
from django.utils import timezone
from datetime import timedelta

class Partner(models.Model):
    STATUS_CHOICES = [
        ('0', 'Requested'),
        ('1', 'Document Verification'),
        ('2', 'In-Training'),
        ('3', 'In-Exam'),
        ('4', 'Activated'),
        ('5', 'Inactive'),
        ('6', 'Rejected'),
    ]

    INTRAINING_STATUS_CHOICES = [
        ('0', 'Eligible'),
        ('1', 'In-Training'),
        ('2', 'Completed'),
    ]

    user_id = models.IntegerField(null=True, blank=True)
    pan_no = models.CharField(max_length=20, blank=True, null=True)
    aadhaar_no = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(max_length=100, blank=True, null=True)
    phone = models.CharField(max_length=15, blank=True, null=True)
    training_started_at = models.CharField(max_length=50, blank=True, null=True)
    exam_completed_at = models.CharField(max_length=50, blank=True, null=True)
    name = models.CharField(max_length=100)
    partner_status = models.CharField(
        max_length=1,  # since it's a single-digit string
        choices=STATUS_CHOICES,
        default='0',
        blank=True,
        null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    active = models.BooleanField(default=True)
    doc_status = models.CharField(
        max_length=10,
        default='0',
        blank=True,
        null=True
    )
    intraining_status =models.CharField(
        max_length=1,
        choices=INTRAINING_STATUS_CHOICES,
        default='0',
        blank=True,
        null=True
        ) ## for intraining status
    
    training_start_date =models.DateTimeField(null=True,blank=True)
    exam_start_date     = models.DateTimeField(null=True, blank=True)
    exam_end_date       = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'partners'

    @property
    def user(self):
        from ..models import Users  # Lazy import inside the method to avoid circular import
        try:
            return Users.objects.get(id=self.user_id)
        except Users.DoesNotExist:
            return None
    
    def start_training_and_exam(self):
        """
        1) If just Activated (4) → start 5‑day training (2)
        2) If in Training (2) and ≥5 days passed → start Exam (3)
        3) If in Exam (3) and ≥7 days passed → re-activate (4)
        """
        now = timezone.now()
        updates = []

        # 1) Activated → In-Training
        if self.partner_status == '4' and self.training_start_date is None:
            self.partner_status    = '2'
            self.intraining_status = '1'
            self.training_start_date = now
            updates += ['partner_status', 'intraining_status', 'training_start_date']

        # 2) In-Training → In-Exam (after 5 days)
        if (self.partner_status == '2' 
            and self.training_start_date 
            and self.exam_start_date is None
            and now >= self.training_start_date + timedelta(days=5)
        ):
            self.partner_status    = '3'
            self.intraining_status = '2'
            self.exam_start_date   = self.training_start_date + timedelta(days=5)
            updates += ['partner_status', 'intraining_status', 'exam_start_date']

        # 3) In-Exam → Activated (after 7 more days)
        if (self.partner_status == '3' 
            and self.exam_start_date 
            and self.exam_end_date is None
            and now >= self.exam_start_date + timedelta(days=7)
        ):
            self.partner_status    = '4'
            self.intraining_status = '0'
            self.exam_end_date     = self.exam_start_date + timedelta(days=7)
            updates += ['partner_status', 'intraining_status', 'exam_end_date']

        if updates:
            # Remove duplicates and save only changed fields
            self.save(update_fields=list(dict.fromkeys(updates)))

    # def update_training_status(self):
    #     now = timezone.now()

    #     # Training End → Exam Opens (2 → 3, 1 → 2) after 5 days
    #     if self.partner_status == '2' and self.training_start_date:
    #         if now >= self.training_start_date + timedelta(days=5) and self.exam_start_date is None:
    #             self.partner_status = '3'  # In-Exam
    #             self.intraining_status = '2'  # Completed Training
    #             self.exam_start_date = now
    #             self.save()

    #     # Exam End → Re-Activation (3 → 4, 2 → 0) after 7 days of exam
    #     if self.partner_status == '3' and self.exam_start_date:
    #         if now >= self.exam_start_date + timedelta(days=7):
    #             self.partner_status = '4'  # Activated
    #             self.intraining_status = '0'  # Eligible
    #             self.exam_end_date = now
    #             self.save()