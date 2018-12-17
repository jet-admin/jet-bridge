from serializers import Serializer, CharField, BooleanField


class ModelDescriptionFieldSerializer(Serializer):
    name = CharField()
    field = CharField()
    db_column = CharField()

    class Meta:
        fields = (
            'name',
            'field',
            'db_column',
        )


class ModelDescriptionSerializer(Serializer):
    model = CharField()
    db_table = CharField()
    hidden = BooleanField()
    fields = ModelDescriptionFieldSerializer(many=True)

    class Meta:
        fields = (
            'model',
            'db_table',
            'hidden',
            'fields'
        )
