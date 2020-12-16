from django.core.serializers.python import Serializer


class LazyLikeEncoder(Serializer):
    def get_dump_object(self, obj):
        dump_object = {}
