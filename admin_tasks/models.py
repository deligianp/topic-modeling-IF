from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models


# Create your models here.

class DataProcessingNode(models.Model):
    host = models.GenericIPAddressField(protocol="IPv4", unique=True)
    username = models.CharField(max_length=32)
    withdrawal_directory = models.CharField(max_length=512)

    def __str__(self):
        return self.username + "@" + self.host


class FileGroup(models.Model):
    name = models.CharField(max_length=32, unique=True)
    description = models.CharField(max_length=64)

    def __str__(self):
        return str(self.name)


class FileExtension(models.Model):
    extension = models.CharField(max_length=32)
    file_group = models.ForeignKey(FileGroup, on_delete=models.CASCADE)

    def __str__(self):
        return "." + self.extension + " - " + self.file_group.name