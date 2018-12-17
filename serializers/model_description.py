from serializers import Serializer, CharField, BooleanField


class ModelDescriptionFieldSerializer(Serializer):
    name = CharField()
    date_type = CharField()
    db_column = CharField()

    class Meta:
        fields = (
            'name',
            'db_column',
            'date_type',
        )


class ModelDescriptionSerializer(Serializer):
    name = CharField()
    db_table = CharField()
    hidden = BooleanField()
    fields = ModelDescriptionFieldSerializer(many=True)

    class Meta:
        fields = (
            'name',
            'db_table',
            'hidden',
            'fields',
        )
