from django.db import models, transaction
from netbox.models import PrimaryModel
from .setting import Source


class Planning(PrimaryModel):
    source = models.ForeignKey(Source, on_delete=models.CASCADE)
    external_id = models.CharField(max_length=32)
    name = models.CharField(max_length=100, unique=True, editable=False)
    disabled = models.BooleanField(editable=False)
    selected = models.BooleanField(default=False)
    last_synced = models.DateTimeField(blank=True, null=True, editable=False)

    class Meta:
        ordering = ("name",)

    def __str__(self):
        return f"{self.name} of {self.source.name}"

    # def get_absolute_url(self):
    #     return reverse("plugins:slurpit_netbox:source_planning", args=[self.pk])

    @classmethod
    def sync(cls, source: Source):
        session = source.get_session()
        r = session.get('/api/planning')
        r.raise_for_status()
        old_planning = {p.external_id: p for p in Planning.objects.all()}
        new_planning = {p['id']: p for p in r.json()}
        old_ids = set(old_planning.keys())
        new_ids = set(new_planning.keys())

        with transaction.atomic():
            for new_id in set(new_ids) - set(old_ids):
                p = new_planning[new_id]
                kw = {k: v for k, v in p.items() if k in ('name', 'disabled')}
                Planning.objects.create(source=source, description=p['comment'], external_id=str(p['id']), **kw)
            obsolete_ids = {old_planning[old_id].id for old_id in set(old_ids) - set(new_ids)}
            Planning.objects.filter(pk__in=obsolete_ids).delete()

            qs = Planning.objects.filter(external_id__in=set(new_ids) & set(old_ids))
            for q in qs:
                p = new_planning[q.external_id]
                q.name = p['name']
                q.disabled = p['disabled']
                q.comments = p['description']
                q.save()
