from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.views.generic.base import TemplateResponseMixin, View
from django.views.generic.detail import DetailView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.apps import apps
from django.forms.models import modelform_factory
from django.db.models import Count
from .models import Subject, Course, Module, Content
from .forms import ModuleFormSet
from braces.views import CsrfExemptMixin, JSONResponseMixin
from students.forms import CourseEnrollForm


class CourseListView(TemplateResponseMixin, View):
    model = Course
    template_name = 'courses/manage/course/list.html'

    def get(self, request, subject=None):
        subjects = Subject.objects.annotate(total_courses=Count('courses'))  # Retrieves all subjects.
        courses = Course.objects.annotate(total_courses=Count('modules'))  # Retrieves all available courses.
        if subject:
            subject = get_object_or_404(Subject, slug=subject)
            courses = courses.filter(subject=subject)
        return self.render_to_response({'subjects': subjects, 'subject': subject, 'courses': courses})


class CourseDetailView(DetailView):
    model = Course
    template_name = 'courses/course/detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['enroll_form'] = CourseEnrollForm(
            initial={'course': self.object})
        return context

class OwnerMixin:
    """
    Implements method to overrides get_queryset to filter objects by the owner attribute
    to retrieve objects that belong to the current user.
    """
    def get_queryset(self):
        qs = super(OwnerMixin, self).get_queryset()
        return qs.filter(owner=self.request.user)


class OwnerEditMixin:
    """Implements method which is executed when the submitted form is valid."""
    def form_valid(self, form):
        form.instance.owner = self.request.user
        return super(OwnerEditMixin, self).form_valid(form)


class OwnerCourseMixin(OwnerMixin, LoginRequiredMixin, PermissionRequiredMixin):
    model = Course  # Model used for QuerySets; it is used by all views.
    fields = ['subject', 'title', 'slug', 'overview']
    success_url = reverse_lazy('manage_course_list')


class OwnerCourseEditMixin(OwnerCourseMixin, OwnerEditMixin):
    fields = ['subject', 'title', 'slug', 'overview']  # The fields of the model to build the model form (CreateView, UpdateView).
    success_url = reverse_lazy('manage_course_list')  # Redirects the user when the form is submitted or deleted.
    template_name = 'courses/manage/course/form.html'


class ManageCourseListView(OwnerCourseMixin, ListView):
    """Lists the courses created by the use"""
    template_name = 'courses/manage/course/list.html'
    permission_required = 'courses.view_course'


class CourseCreateView(OwnerCourseEditMixin, CreateView):
    """Uses a model form to create a new Course object."""
    permission_required = 'courses.add_course'


class CourseUpdateView(OwnerCourseEditMixin, UpdateView):
    """Allows the editing of an existing Course object"""
    permission_required = 'courses.change_course'


class CourseDeleteView(OwnerCourseMixin, DeleteView):
    """
    It defines a specific template_name attribute for a template
    to confirm the course deletion.
    """
    template_name = 'courses/manage/course/delete.html'
    success_url = reverse_lazy('manage_course_list')
    permission_required = 'courses.delete_course'


class CourseModuleUpdateView(TemplateResponseMixin, View):
    """
    Handles the formset to add, update, and delete modules for a specific course.
    """
    template_name = 'courses/manage/module/formset.html'
    course = None

    # Method responsible to avoid repeating the code to build the formset.
    def get_formset(self, data=None):
        return ModuleFormSet(instance=self.course, data=data)

    # Takes an HTTP request and its parameters and attempts to delegate to a lowercase method that matches the HTTP method used.
    # A GET request is delegated to the get() method and a POST request to post(), respectively
    def dispatch(self, request, pk):
        self.course = get_object_or_404(Course, id=pk, owner=request.user)
        return super().dispatch(request, pk)

    def get(self, request, *args, **kwargs):
        formset = self.get_formset()
        return self.render_to_response({'course': self.course, 'formset': formset})

    def post(self, request, *args, **kwargs):
        formset = self.get_formset(data=request.POST)
        if formset.is_valid():
            formset.save()
            return redirect('manage_course_list')
        return self.render_to_response({'course': self.course, 'formset': formset})


class ContentCreateUpdateView(TemplateResponseMixin, View):
    module = None
    model = None
    obj = None
    template_name = 'courses/manage/content/form.html'

    # check that the given model name is one of the four content, then obtain the actual class for the given model name.
    def get_model(self, model_name):
        if model_name in ['text', 'video', 'image', 'file']:
            return apps.get_model(app_label='courses', model_name=model_name)
        return None

    def get_form(self, model, *args, **kwargs):
        # uses the exclude parameter to specify the common fields to exclude from the form and let all other
        # attributes be included automatically.
        Form = modelform_factory(model, exclude=['owner', 'order', 'created', 'updated'])
        return Form(*args, **kwargs)

    # Receives the following URL parameters and stores the corresponding module, model, content object as class attrs.
    def dispatch(self, request, module_id, model_name, id=None):
        self.module = get_object_or_404(Module, id=module_id, course__owner=request.user)
        self.model = self.get_model(model_name)
        if id:
            self.obj = get_object_or_404(self.model, id=id, owner=request.user)
        return super(ContentCreateUpdateView, self).dispatch(request, module_id, model_name, id)

    # Executed when a GET request is received. If passes no instance then creates a new object.
    def get(self, request, module_id, model_name, id=None):
        form = self.get_form(self.model, instance=self.obj)
        return self.render_to_response({'form': form, 'object': self.obj})

    def post(self, request, module_id, model_name, id=None):
        """
        1. Build the model form and passing data to it.
        2. If form is valid then creates new object and assign request.user.
        3. check id and if no id then create Content object for specific module and associate with it.
        """
        form = self.get_form(self.model, instance=self.obj, data=request.POST, files=request.FILES)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.owner = request.user
            obj.save()
        if not id:
            Content.objects.create(module=self.module, item=obj)  # new content
            return redirect('module_content_list', self.module.id)
        return self.render_to_response({'form': form, 'object': self.obj})


class ContentDeleteView(View):
    """
    Retrieves the Content object with the given ID. It deletes the Content object and redirects the user
    to the module_content_list URL to list the other contents of the module.
    """

    def post(self, request, id):
        content = get_object_or_404(Content, id=id, course__owner=request.user)
        module = content.module
        content.item.delete()
        content.delete()
        return redirect('module_content_list', module.id)


class ModuleContentListView(TemplateResponseMixin, View):
    template_name = 'courses/manage/module/content_list.html'

    def get(self, request, module_id):
        module = get_object_or_404(Module, id=module_id, course__owner=request.user)
        return self.render_to_response({'module': module})


class ModuleOrderView(CsrfExemptMixin, JSONResponseMixin, View):
    def post(self, request):
        for id, order in self.request_json.items():
            Module.objects.filter(id=id, course__owner=request.user).update(order=order)
        return self.render_json_response({'saved': 'OK'})


class ContentOrderView(CsrfExemptMixin, JSONResponseMixin, View):
    def post(self, request):
        for id, order in self.request_json.items():
            Content.objects.filter(id=id, module__course__owner=request.user).update(order=order)
        return self.render_json_response({'saved': 'OK'})


