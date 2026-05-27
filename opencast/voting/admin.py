from django.contrib import admin
from django.utils.html import format_html
from .models import Event, Category, Nominee, Transaction, Vote


class CategoryInline(admin.TabularInline):
    model = Category
    extra = 1
    show_change_link = True


class NomineeInline(admin.TabularInline):
    model = Nominee
    extra = 1
    fields = ['name', 'photo', 'vote_count', 'is_active']
    readonly_fields = ['vote_count']


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'price_per_vote', 'bundle_info',
        'is_active', 'show_results', 'bundle_enabled', 'is_open_display',
        'start_date', 'end_date'
    ]
    list_editable = ['is_active', 'show_results', 'bundle_enabled', 'price_per_vote']
    list_filter = ['is_active', 'show_results']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}
    inlines = [CategoryInline]
    fieldsets = (
        ('Event Info', {
            'fields': ('name', 'slug', 'description', 'banner')
        }),
        ('Voting Pricing', {
            'fields': ('price_per_vote', 'bundle_enabled', 'bundle_size', 'bundle_price', 'max_votes_per_transaction'),
            'description': 'Set price per vote. Enable bundle pricing to sell votes in packs.',
        }),
        ('Visibility & Schedule', {
            'fields': ('is_active', 'show_results', 'start_date', 'end_date')
        }),
    )

    def is_open_display(self, obj):
        if obj.is_open:
            return format_html('<span style="color:green;font-weight:bold;">● Open</span>')
        return format_html('<span style="color:red;">● Closed</span>')
    is_open_display.short_description = 'Status'

    def bundle_info(self, obj):
        if obj.bundle_enabled and obj.bundle_size > 1 and obj.bundle_price:
            return f"ON — {obj.bundle_size} votes / GHS {obj.bundle_price}"
        return "Off"
    bundle_info.short_description = 'Bundle'


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'event', 'order']
    list_filter = ['event']
    search_fields = ['name', 'event__name']
    inlines = [NomineeInline]


@admin.register(Nominee)
class NomineeAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'event_name', 'vote_count', 'is_active']
    list_filter = ['category__event', 'is_active']
    search_fields = ['name', 'category__name']
    readonly_fields = ['vote_count']

    def event_name(self, obj):
        return obj.category.event.name
    event_name.short_description = 'Event'


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = [
        'short_ref', 'voter_email', 'nominee_name', 'event_name',
        'num_votes', 'amount_display', 'status_badge', 'created_at'
    ]
    list_filter = ['status', 'nominee__category__event']
    search_fields = ['voter_email', 'reference', 'paystack_reference']
    readonly_fields = [
        'reference', 'paystack_reference', 'nominee',
        'voter_email', 'voter_phone', 'num_votes', 'amount',
        'price_per_vote_snapshot', 'ip_address', 'created_at', 'updated_at'
    ]
    date_hierarchy = 'created_at'

    def short_ref(self, obj):
        return str(obj.reference)[:8].upper()
    short_ref.short_description = 'Ref'

    def nominee_name(self, obj):
        return obj.nominee.name
    nominee_name.short_description = 'Nominee'

    def event_name(self, obj):
        return obj.nominee.category.event.name
    event_name.short_description = 'Event'

    def amount_display(self, obj):
        return f"GHS {obj.amount}"
    amount_display.short_description = 'Amount'

    def status_badge(self, obj):
        colors = {
            'success': 'green',
            'pending': 'orange',
            'failed': 'red',
            'abandoned': 'grey',
        }
        color = colors.get(obj.status, 'black')
        return format_html(
            '<span style="color:{};font-weight:bold;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'


@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    list_display = ['nominee', 'num_votes', 'created_at']
    list_filter = ['nominee__category__event']
    readonly_fields = ['transaction', 'nominee', 'num_votes', 'created_at']
