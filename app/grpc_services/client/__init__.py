"""
gRPC客户端module - alreadyrefactored为usesharedcore service
注：原来 AnalysisClientalready被remove，nowdirectlyuseCoreAnalysisService
"""

# thismodule保留为空，以防未来需要add其他gRPC客户端
# currentarchitectureusesharedcore service层，avoidingin部networkcalloverhead

__all__ = []