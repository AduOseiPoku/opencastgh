import uuid
from django.db import models
from django.db.models import F
from django.utils import timezone
from django.contrib.auth.models import User


class Event(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, max_length=255)
    description = models.TextField(blank=True)
    banner = models.ImageField(upload_to='events/', blank=True, null=True)
    price_per_vote = models.DecimalField(
        max_digits=8, decimal_places=2,
        help_text="Price in GHS per single vote"
    )
    # Optional: sell votes in bundles (e.g. 5 votes for GHS 4)
    bundle_enabled = models.BooleanField(
        default=False,
        help_text="Toggle bundle pricing on or off."
    )
    bundle_size = models.PositiveIntegerField(
        default=1,
        help_text="Number of votes per bundle."
    )
    bundle_price = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True,
        help_text="Price for one bundle."
    )
    is_active = models.BooleanField(default=True)
    show_results = models.BooleanField(
        default=False,
        help_text="Whether vote counts are visible to the public."
    )
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-start_date']

    def __str__(self):
        return self.name

    @property
    def is_open(self):
        now = timezone.now()
        return self.is_active and self.start_date <= now <= self.end_date

    def get_price_for_votes(self, num_votes):
        """Calculate total price for a given number of votes."""
        if self.bundle_enabled and self.bundle_size > 1 and self.bundle_price:
            import math
            bundles = math.ceil(num_votes / self.bundle_size)
            return bundles * self.bundle_price
        return self.price_per_vote * num_votes


class Category(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='categories')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'name']
        verbose_name_plural = 'Categories'

    def __str__(self):
        return f"{self.event.name} — {self.name}"


class Nominee(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='nominees')
    name = models.CharField(max_length=255)
    bio = models.TextField(blank=True)
    photo = models.ImageField(upload_to='nominees/', blank=True, null=True)
    vote_count = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.category.name})"

    def increment_votes(self, count=1):
        """Atomic vote increment — safe under concurrent load."""
        Nominee.objects.filter(pk=self.pk).update(vote_count=F('vote_count') + count)


class Transaction(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        SUCCESS = 'success', 'Success'
        FAILED = 'failed', 'Failed'
        ABANDONED = 'abandoned', 'Abandoned'

    reference = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    nominee = models.ForeignKey(Nominee, on_delete=models.PROTECT, related_name='transactions')
    voter_name = models.CharField(max_length=255, blank=True)
    voter_email = models.EmailField()
    voter_phone = models.CharField(max_length=20, blank=True)
    num_votes = models.PositiveIntegerField(default=1)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    # Snapshot the price at time of transaction creation
    price_per_vote_snapshot = models.DecimalField(max_digits=8, decimal_places=2)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    paystack_reference = models.CharField(max_length=255, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"TXN-{str(self.reference)[:8].upper()} | {self.voter_email} | {self.get_status_display()}"

    @property
    def reference_str(self):
        return str(self.reference)


class Vote(models.Model):
    """Created only after a Transaction is confirmed successful."""
    transaction = models.OneToOneField(Transaction, on_delete=models.PROTECT, related_name='vote')
    nominee = models.ForeignKey(Nominee, on_delete=models.PROTECT, related_name='votes')
    num_votes = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.num_votes} vote(s) for {self.nominee.name} via {self.transaction}"
