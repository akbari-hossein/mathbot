from rest_framework import serializers
from .models import Contest, Participation
from django.utils import timezone


class ParticipationSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = Participation
        fields = ['username', 'joined_at']
        read_only_fields = ['joined_at']


class ContestSignupSerializer(serializers.Serializer):
    def validate(self, data):
        contest = self.context['contest']
        user = self.context['request'].user
        
        # Check if user is already participating
        if Participation.objects.filter(contest=contest, user=user).exists():
            raise serializers.ValidationError("شما قبلا در این مسابقه ثبت نام کرده‌اید")
        
        # Check if contest has started
        if contest.start_time <= timezone.now():
            raise serializers.ValidationError("زمان ثبت نام این مسابقه به پایان رسیده است")
            
        return data


class ContestListSerializer(serializers.ModelSerializer):
    participations = ParticipationSerializer(many=True, read_only=True)
    participation_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Contest
        fields = ['id', 'title', 'description', 'start_time', 'price', 'image', 'participations', 'participation_count']
    
    def get_participation_count(self, obj):
        return obj.participations.count()