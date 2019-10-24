from django.db import models
from django.utils.translation import ugettext_lazy as _


class Token(models.Model):
    project = models.CharField(
        verbose_name=_('project'),
        max_length=30,
        blank=True,
        default=''
    )
    token = models.UUIDField(
        verbose_name=_('token')
    )
    date_add = models.DateTimeField(
        verbose_name=_('date added')
    )

    class Meta:
        verbose_name = _('token')
        verbose_name_plural = _('tokens')
        db_table = '__jet__token'
        managed = False

    def __str__(self):
        return str(self.token)
