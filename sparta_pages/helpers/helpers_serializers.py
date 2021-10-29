# Custom Block Serializers (to not use requests @_@)
from lms.djangoapps.course_api.blocks.serializers import BlockDictSerializer, BlockSerializer, SUPPORTED_FIELDS
# from lms.djangoapps.course_api.blocks.transformers import SUPPORTED_FIELDS

import logging
logger = logging.getLogger(__name__)


class CoursebankBlockSerializer(BlockSerializer):  # pylint: disable=abstract-method
    """
    Custom Serializer for single course block
    """
    def to_representation(self, block_key):
        """
        Return a serializable representation of the requested block
        """
        # create response data dict for basic fields
        data = {
            'id': unicode(block_key),
            'block_id': unicode(block_key.block_id),
        }

        # add additional requested fields that are supported by the various transformers
        for supported_field in SUPPORTED_FIELDS:
            if supported_field.requested_field_name in self.context['requested_fields']:
                field_value = self._get_field(
                    block_key,
                    supported_field.transformer,
                    supported_field.block_field_name,
                    supported_field.default_value,
                )
                if field_value is not None:
                    # only return fields that have data
                    data[supported_field.serializer_field_name] = field_value


        if 'children' in self.context['requested_fields']:
            children = self.context['block_structure'].get_children(block_key)
            if children:
                data['children'] = [unicode(child) for child in children]

        return data

class CoursebankBlockDictSerializer(BlockDictSerializer):  # pylint: disable=abstract-method
    """
    Serializer that formats a BlockStructure object to a dictionary, rather
    than a list, of blocks
    """

    def get_blocks(self, structure):
        """
        Serialize to a dictionary of blocks keyed by the block's usage_key.
        """
        return {
            unicode(block_key): CoursebankBlockSerializer(block_key, context=self.context).data
            for block_key in structure
        }
