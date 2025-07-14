from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.hashers import check_password, make_password
from .services import DatabaseService
import logging

logger = logging.getLogger(__name__)


class RoleSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(max_length=20)
    display_name = serializers.CharField(max_length=50)
    description = serializers.CharField(allow_blank=True)


class UserSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    email = serializers.EmailField()
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    role_id = serializers.IntegerField(write_only=True, required=False)
    role_detail = RoleSerializer(read_only=True)
    role_name = serializers.CharField(read_only=True)
    is_active = serializers.BooleanField(default=True)
    date_joined = serializers.DateTimeField(read_only=True)
    
    def to_representation(self, instance):
        """Convert database response to serialized format"""
        if isinstance(instance, dict):
            data = super().to_representation(instance)
            # Add role_detail if role information exists
            if 'role' in instance and isinstance(instance['role'], dict):
                data['role_detail'] = instance['role']
                data['role_name'] = instance['role'].get('name', '')
            return data
        return super().to_representation(instance)


class UserRegistrationSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True, required=True)
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    role = serializers.CharField(write_only=True, required=True)
    
    def validate_email(self, value):
        # Check if user already exists
        existing_user = DatabaseService.get_user_by_email(value)
        if existing_user:
            raise serializers.ValidationError("User with this email already exists.")
        return value
    
    def validate_role(self, value):
        valid_roles = ['PATIENT', 'CLINICIAN']
        if value not in valid_roles:
            raise serializers.ValidationError(f"Invalid role. Choose either {' or '.join(valid_roles)}.")
        return value
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        role_name = validated_data.pop('role')
        
        # Get role from database service
        role = DatabaseService.get_role_by_name(role_name)
        if not role:
            # Create role if it doesn't exist
            roles = DatabaseService.get_roles()
            role = next((r for r in roles if r['name'] == role_name), None)
            
        if not role:
            raise serializers.ValidationError({"role": "Role not found"})
        
        # Hash the password
        password = validated_data.pop('password')
        password_hash = make_password(password)
        
        # Create user via database service
        user_data = {
            'email': validated_data['email'],
            'password': password_hash,
            'first_name': validated_data['first_name'],
            'last_name': validated_data['last_name'],
            'role': role['id'],
            'is_active': True
        }
        
        try:
            user = DatabaseService.create_user(user_data)
            # Store the role name in validated_data so it can be accessed in the view
            self.validated_data['role'] = role_name
            return user
        except Exception as e:
            logger.error(f"Failed to create user: {e}")
            raise serializers.ValidationError({"error": "Failed to create user"})


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, write_only=True)
    
    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')
        
        if email and password:
            # Get user from database service
            user = DatabaseService.get_user_by_email(email)
            
            if not user:
                raise serializers.ValidationError('Invalid email or password.')
            
            # Check password
            if not check_password(password, user.get('password', '')):
                raise serializers.ValidationError('Invalid email or password.')
            
            if not user.get('is_active', False):
                raise serializers.ValidationError('User account is disabled.')
            
            attrs['user'] = user
        else:
            raise serializers.ValidationError('Must include "email" and "password".')
        
        return attrs


class RefreshTokenSerializer(serializers.Serializer):
    refresh_token = serializers.CharField(required=True)


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True, validators=[validate_password])
    new_password_confirm = serializers.CharField(required=True, write_only=True)
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({"new_password": "New password fields didn't match."})
        return attrs