from __future__ import annotations

from typing import Any

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.core.validators import validate_email
from django.db import models
  
class UserManager(BaseUserManager):
    """Create through create_user and create_superuser"""
    @classmethod
    def normalize_email(cls, email):
        return super().normalize_email(email.strip()).lower()

    def create_user(self, 
        email:str, 
        first_name:str, 
        last_name:str, 
        password:str|None=None,
        **extra_fields:Any,
        ) -> User:
        email = self.normalize_email(email)
        validate_email(email)
        user = self.model(
            email=email,
            first_name=first_name.strip(),
            last_name=last_name.strip(),
            **extra_fields,
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self,
        email:str,
        first_name:str,
        last_name:str,
        password:str|None=None,
        **extra_fields:Any,)->User:
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        return self.create_user(email=email, 
            first_name=first_name,
            last_name=last_name,
            password=password,
            **extra_fields,
        )

class User(AbstractBaseUser, PermissionsMixin):
    """Email based user"""
    NAME_MAX_LENGTH = 70
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=NAME_MAX_LENGTH)
    second_name = models.CharField(max_length=NAME_MAX_LENGTH)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    USERNAME_FIELD = "email"
    objects = UserManager()
  
