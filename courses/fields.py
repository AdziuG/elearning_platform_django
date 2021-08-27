from django.db import models
from django.core.exceptions import ObjectDoesNotExist


class OrderField(models.PositiveIntegerField):
    """
    OrderField field takes an optional for_fields parameter that allows to
    indicate the fields that the order has to be calculated with respect to.
    """
    def __init__(self, for_fields=None, *args, **kwargs):
        self.for_fields = for_fields
        super().__init__(*args, **kwargs)

    def pre_save(self, model_instance, add):
        """
        Field overrides the pre_save() method of the PositiveIntegerField field,
        which is executed before saving the field into the database.
        """
        if getattr(model_instance, self.attname) is None:  # checks whether a value already exists for this fields in model instance.
            # no current value
            try:
                qs = self.model.objects.all()  # retrieve all objects
                if self.for_fields:
                    # filter by objects with the same field values
                    # for the fields in "for_fields"
                    query = {field: getattr(model_instance, field)\
                             for field in self.for_fields}
                    qs = qs.filter(**query)
                # get the order of the last item
                last_item = qs.latest(self.attname)  # retrieve the object with the highest order
                value = last_item.order + 1  # add value the highest object
            except ObjectDoesNotExist:
                value = 0
            setattr(model_instance, self.attname, value)
            return value
        else:
            return super().pre_save(model_instance, add)

