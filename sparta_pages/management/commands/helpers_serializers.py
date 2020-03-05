# Custom Block Serializers (to not use requests @_@)
from lms.djangoapps.course_api.blocks.serializers import BlockDictSerializer, BlockSerializer

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
