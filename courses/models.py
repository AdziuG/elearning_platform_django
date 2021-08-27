from django.db import models
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from .fields import OrderField


class Subject(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)

    class Meta:
        ordering = ("title",)

    def __str__(self):
        return self.title


class Course(models.Model):
    """

    """
    owner = models.ForeignKey(User,
                              related_name='courses_created',
                              on_delete=models.CASCADE)  # The instructor who created this course.
    subject = models.ForeignKey(Subject,
                                related_name='courses',
                                on_delete=models.CASCADE)  # Creates subject within course.
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    overview = models.TextField()
    created = models.DateTimeField(auto_now_add=True)  # It will be automatically set by Django.

    class Meta:
        ordering = ('-created',)

    def __str__(self):
        return self.title


class Module(models.Model):
    course = models.ForeignKey(Course,
                               related_name='modules',
                               on_delete=models.CASCADE)  # Every course is split on many modules.
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    order = OrderField(blank=True, for_fields=['course'])  # Order for a new module will be assigned by adding 1 to the last module of the same Course object.

    def __str__(self):
        return f'{self.order}. {self.title}'

    class Meta:
        ordering = ['order']  # default ordering


class Content(models.Model):
    """
    Represents content in module class
    """
    module = models.ForeignKey(Module, related_name='contents', on_delete=models.CASCADE)
    content_type = models.ForeignKey(ContentType,
                                     limit_choices_to={'model_in': ('text', # Limited objects that can be used for the generic relation
                                                                   'video',
                                                                   'image',
                                                                   'file')},
                                     on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()  # Store the primary key of the related object.
    item = GenericForeignKey('content_type', 'object_id')  # The field to the related object combining the two previous fields.
    order = OrderField(blank=True, for_fields=['module'])  # The order is calculated with respect to the module field.

    class Meta:
        ordering = ['order']  # default ordering


class ItemBase(models.Model):
    """
    The abstract model that provides the common fields for all content models.
    """
    owner = models.ForeignKey(User,
                              related_name='%(class)s_related',  # Different for each sub-class, model class name, generated automatically.
                              on_delete=models.CASCADE)  # store which user created the content
    title = models.CharField(max_length=250)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

    def __str__(self):
        return self.title


class Text(ItemBase):
    """Stores text content"""
    content = models.TextField()


class File(ItemBase):
    """Stores files"""
    file = models.FileField(upload_to='files')


class Image(ItemBase):
    """Stores image files"""
    file = models.FileField(upload_to='images')


class Video(ItemBase):
    """Store videos; uses URLField field to provide a video URL in order to embed it"""
    url = models.URLField()