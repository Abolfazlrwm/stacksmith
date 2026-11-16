"""Serializers — validate input and shape output for the API."""
from rest_framework import serializers

from .models import Conversation, Message


class CitationSerializer(serializers.Serializer):
    chunk_id = serializers.IntegerField()
    document_id = serializers.IntegerField()
    document_title = serializers.CharField()
    ordinal = serializers.IntegerField()
    score = serializers.FloatField()
    snippet = serializers.CharField()


class MessageSerializer(serializers.ModelSerializer):
    citations = CitationSerializer(many=True, read_only=True)

    class Meta:
        model = Message
        fields = ("id", "role", "content", "citations", "retrieved_count",
                  "model", "created_at")
        read_only_fields = ("id", "role", "citations", "retrieved_count",
                            "model", "created_at")


class ConversationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Conversation
        fields = ("id", "title", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")


class ChatRequestSerializer(serializers.Serializer):
    """POST /api/chat/ — ask one question."""
    question = serializers.CharField(max_length=4000)
    conversation_id = serializers.IntegerField(required=False, allow_null=True)
    top_k = serializers.IntegerField(required=False, default=5, min_value=1, max_value=20)


class ChatResponseSerializer(serializers.Serializer):
    answer = serializers.CharField()
    conversation_id = serializers.IntegerField()
    message_id = serializers.IntegerField()
    citations = CitationSerializer(many=True)
    retrieved_count = serializers.IntegerField()
    model = serializers.CharField()
