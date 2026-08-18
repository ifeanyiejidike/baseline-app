import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.core.context import tenant_context
from apps.customers.models import Customer
from apps.documents.models import Document
from apps.projects.models import Project


def _make_file(name="test.pdf", content=b"%PDF-1.4 fake content"):
    return SimpleUploadedFile(name, content, content_type="application/pdf")


class TestDocumentOwnership:
    def test_exactly_one_owner_customer_is_valid(self, org_factory):
        org = org_factory()
        with tenant_context(org.id):
            customer = Customer.objects.create(name="Client Co")
            doc = Document(
                customer=customer,
                file=_make_file(),
                original_filename="test.pdf",
                size_bytes=100,
            )
            doc.save()
            assert doc.owner == customer

    def test_zero_owners_raises(self, org_factory):
        org = org_factory()
        with tenant_context(org.id):
            doc = Document(file=_make_file(), original_filename="test.pdf", size_bytes=100)
            with pytest.raises(ValidationError):
                doc.save()

    def test_two_owners_raises(self, org_factory):
        org = org_factory()
        with tenant_context(org.id):
            customer = Customer.objects.create(name="Client Co")
            project = Project.objects.create(name="Some Project")
            doc = Document(
                customer=customer, project=project, file=_make_file(), original_filename="test.pdf", size_bytes=100
            )
            with pytest.raises(ValidationError):
                doc.save()

    def test_delete_removes_underlying_file(self, org_factory, settings, tmp_path):
        settings.MEDIA_ROOT = str(tmp_path)
        org = org_factory()
        with tenant_context(org.id):
            customer = Customer.objects.create(name="Client Co")
            doc = Document.objects.create(
                customer=customer, file=_make_file(), original_filename="test.pdf", size_bytes=100
            )
            file_path = doc.file.path
            import os

            assert os.path.exists(file_path)
            doc.file.delete(save=False)
            doc.delete()
            assert not os.path.exists(file_path)
