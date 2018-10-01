from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from rest_framework.generics import (
    ListCreateAPIView,
    RetrieveUpdateDestroyAPIView
)
from rest_framework import pagination
from rest_framework import status
from rest_framework import filters
from rest_framework.permissions import (
    IsAuthenticated,
)
from rest_framework.response import Response
from events.models import (
    EventType,
    Event,
)
from .serializers import (
    EventTypeSerializer,
    EventSerializer,
)
from model_utils import Choices


class EventTypeListCreateAPIView(ListCreateAPIView):
    serializer_class = EventTypeSerializer
    queryset = EventType.objects.all()
    permission_classes = [IsAuthenticated]


class EventTypeRetrieveUpdateDestroyAPIView(RetrieveUpdateDestroyAPIView):
    serializer_class = EventTypeSerializer
    queryset = EventType.objects.all()
    permission_classes = [IsAuthenticated]
    
    
class EventRetrieveUpdateDestroyAPIView(RetrieveUpdateDestroyAPIView):
    serializer_class = EventSerializer
    queryset = Event.objects.all()
    permission_classes = [IsAuthenticated]
    

class EventListCreateAPIView(ListCreateAPIView):
    serializer_class = EventSerializer
    permission_classes = [IsAuthenticated]

    # for DataTable.js ordering
    ORDER_COLUMN_CHOICES = Choices(
        ('2', 'date'),
        ('3', 'type__id'),
        ('4', 'name'),
        ('5', 'context'),
    )

    # check if request arguments "content_type_id", "object_id" advised
    filter_by_product = False
    datatable = False
    content_type_id = None
    object_id = None

    def initial(self, request, *args, **kwargs):
        super(EventListCreateAPIView, self).initial(request, *args, **kwargs)

        # setting
        self.content_type_id = request.query_params.get('content_type_id', None)
        self.object_id = request.query_params.get('object_id', None)
        self.datatable = request.query_params.get('datatable', None) == 'true'
        self.filter_by_product = bool(self.content_type_id and self.object_id)

    def get_queryset(self):

        queryset = Event.objects.all().order_by('-date')

        if not self.filter_by_product:
            return queryset

        content_type = ContentType.objects.get(id=self.content_type_id)
        instance = content_type.model_class().objects.get(id=self.object_id)

        if content_type.model == 'config':
            product_ids = instance.products().values_list('id', flat=True)
            queryset = queryset.filter(content_type__model='abstractproduct', object_id__in=product_ids)
        elif content_type.model == 'abstractproduct':
            product_ids = list(instance.children_all().values_list('id', flat=True))
            product_ids.append(instance.id)
            queryset = queryset.filter(content_type__model='abstractproduct', object_id__in=product_ids)
        else:
            queryset = queryset.none()

        return queryset

    def get_datatable_data(self):

        kwargs = self.request.query_params

        draw = int(kwargs.get('draw', None) or 0)
        length = int(kwargs.get('length', None) or 0)
        start = int(kwargs.get('start', None) or 0)
        search_value = kwargs.get('search[value]', None)
        order_column = kwargs.get('order[0][column]', None)
        order = kwargs.get('order[0][dir]', None)

        order_column = self.ORDER_COLUMN_CHOICES[order_column]
        # django orm '-' -> desc
        if order == 'desc':
            order_column = '-' + order_column

        queryset = self.get_queryset()
        total = queryset.count()

        if search_value:
            queryset = queryset.filter(Q(id__icontains=search_value) |
                                       Q(name__icontains=search_value) |
                                       Q(context__icontains=search_value) |
                                       Q(date__icontains=search_value))

        count = queryset.count()
        queryset = queryset.order_by(order_column)[start:start + length]

        return {
            'items': queryset,
            'count': count,
            'total': total,
            'draw': draw,
        }

    def list(self, request, **kwargs):
        if self.datatable:
            try:
                event = self.get_datatable_data()
                serializer = EventSerializer(event['items'], many=True)
                result = {
                    'data': serializer.data,
                    'draw': event['draw'],
                    'recordsTotal': event['total'],
                    'recordsFiltered': event['count'],
                }
                return Response(result, status=status.HTTP_200_OK, template_name=None, content_type=None)

            except Exception as e:
                return Response(e, status=status.HTTP_400_BAD_REQUEST, template_name=None, content_type=None)

        return super(EventListCreateAPIView, self).list(request, **kwargs)