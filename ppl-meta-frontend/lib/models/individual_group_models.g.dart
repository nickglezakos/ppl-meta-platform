// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'individual_group_models.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

IndividualGroup _$IndividualGroupFromJson(Map<String, dynamic> json) =>
    IndividualGroup(
      id: json['id'] as String,
      name: json['name'] as String,
      description: json['description'] as String?,
      createdBy: json['created_by'] as String,
      createdAt: DateTime.parse(json['created_at'] as String),
      updatedAt: DateTime.parse(json['updated_at'] as String),
      memberCount: (json['member_count'] as num).toInt(),
      memberIds: (json['member_ids'] as List<dynamic>)
          .map((e) => e as String)
          .toList(),
      visibility: $enumDecode(_$GroupVisibilityEnumMap, json['visibility']),
      tags: (json['tags'] as List<dynamic>).map((e) => e as String).toList(),
      coverIndividualId: json['cover_individual_id'] as String?,
      metadata: json['metadata'] as Map<String, dynamic>?,
    );

Map<String, dynamic> _$IndividualGroupToJson(IndividualGroup instance) =>
    <String, dynamic>{
      'id': instance.id,
      'name': instance.name,
      'description': instance.description,
      'created_by': instance.createdBy,
      'created_at': instance.createdAt.toIso8601String(),
      'updated_at': instance.updatedAt.toIso8601String(),
      'member_count': instance.memberCount,
      'member_ids': instance.memberIds,
      'visibility': _$GroupVisibilityEnumMap[instance.visibility]!,
      'tags': instance.tags,
      'cover_individual_id': instance.coverIndividualId,
      'metadata': instance.metadata,
    };

const _$GroupVisibilityEnumMap = {
  GroupVisibility.private: 'private',
  GroupVisibility.shared: 'shared',
  GroupVisibility.public: 'public',
};

IndividualSummary _$IndividualSummaryFromJson(Map<String, dynamic> json) =>
    IndividualSummary(
      id: json['id'] as String,
      mvrPersonUuid: json['mvr_person_uuid'] as String?,
      groupMemberNumber: (json['group_member_number'] as num?)?.toInt(),
      thumbnailUrl: json['thumbnail_url'] as String?,
      totalAppearances: (json['total_appearances'] as num).toInt(),
      lastSeen: json['last_seen'] == null
          ? null
          : DateTime.parse(json['last_seen'] as String),
      groupCount: (json['group_count'] as num).toInt(),
      confidenceScore: (json['confidence_score'] as num).toDouble(),
      name: json['name'] as String?,
      nameUpdatedAt: json['name_updated_at'] == null
          ? null
          : DateTime.parse(json['name_updated_at'] as String),
      nameUpdatedBy: json['name_updated_by'] as String?,
    );

Map<String, dynamic> _$IndividualSummaryToJson(IndividualSummary instance) =>
    <String, dynamic>{
      'id': instance.id,
      'mvr_person_uuid': instance.mvrPersonUuid,
      'group_member_number': instance.groupMemberNumber,
      'thumbnail_url': instance.thumbnailUrl,
      'total_appearances': instance.totalAppearances,
      'last_seen': instance.lastSeen?.toIso8601String(),
      'group_count': instance.groupCount,
      'confidence_score': instance.confidenceScore,
      'name': instance.name,
      'name_updated_at': instance.nameUpdatedAt?.toIso8601String(),
      'name_updated_by': instance.nameUpdatedBy,
    };

ListGroupsResponse _$ListGroupsResponseFromJson(Map<String, dynamic> json) =>
    ListGroupsResponse(
      groups: (json['groups'] as List<dynamic>)
          .map((e) => IndividualGroup.fromJson(e as Map<String, dynamic>))
          .toList(),
      total: (json['total'] as num).toInt(),
      skip: (json['skip'] as num).toInt(),
      limit: (json['limit'] as num).toInt(),
    );

Map<String, dynamic> _$ListGroupsResponseToJson(ListGroupsResponse instance) =>
    <String, dynamic>{
      'groups': instance.groups,
      'total': instance.total,
      'skip': instance.skip,
      'limit': instance.limit,
    };

GetGroupResponse _$GetGroupResponseFromJson(Map<String, dynamic> json) =>
    GetGroupResponse(
      group: IndividualGroup.fromJson(json['group'] as Map<String, dynamic>),
      membersPreview: (json['members_preview'] as List<dynamic>)
          .map((e) => IndividualSummary.fromJson(e as Map<String, dynamic>))
          .toList(),
    );

Map<String, dynamic> _$GetGroupResponseToJson(GetGroupResponse instance) =>
    <String, dynamic>{
      'group': instance.group,
      'members_preview': instance.membersPreview,
    };

ListMembersResponse _$ListMembersResponseFromJson(Map<String, dynamic> json) =>
    ListMembersResponse(
      members: (json['members'] as List<dynamic>)
          .map((e) => IndividualSummary.fromJson(e as Map<String, dynamic>))
          .toList(),
      total: (json['total'] as num).toInt(),
      skip: (json['skip'] as num).toInt(),
      limit: (json['limit'] as num).toInt(),
    );

Map<String, dynamic> _$ListMembersResponseToJson(
        ListMembersResponse instance) =>
    <String, dynamic>{
      'members': instance.members,
      'total': instance.total,
      'skip': instance.skip,
      'limit': instance.limit,
    };

CreateGroupRequest _$CreateGroupRequestFromJson(Map<String, dynamic> json) =>
    CreateGroupRequest(
      name: json['name'] as String,
      description: json['description'] as String?,
      visibility:
          $enumDecodeNullable(_$GroupVisibilityEnumMap, json['visibility']) ??
              GroupVisibility.private,
      tags:
          (json['tags'] as List<dynamic>?)?.map((e) => e as String).toList() ??
              const [],
      initialMemberIds: (json['initial_member_ids'] as List<dynamic>?)
              ?.map((e) => e as String)
              .toList() ??
          const [],
    );

Map<String, dynamic> _$CreateGroupRequestToJson(CreateGroupRequest instance) =>
    <String, dynamic>{
      'name': instance.name,
      'description': instance.description,
      'visibility': _$GroupVisibilityEnumMap[instance.visibility]!,
      'tags': instance.tags,
      'initial_member_ids': instance.initialMemberIds,
    };

UpdateGroupRequest _$UpdateGroupRequestFromJson(Map<String, dynamic> json) =>
    UpdateGroupRequest(
      name: json['name'] as String?,
      description: json['description'] as String?,
      visibility:
          $enumDecodeNullable(_$GroupVisibilityEnumMap, json['visibility']),
      tags: (json['tags'] as List<dynamic>?)?.map((e) => e as String).toList(),
      coverIndividualId: json['cover_individual_id'] as String?,
    );

Map<String, dynamic> _$UpdateGroupRequestToJson(UpdateGroupRequest instance) =>
    <String, dynamic>{
      'name': instance.name,
      'description': instance.description,
      'visibility': _$GroupVisibilityEnumMap[instance.visibility],
      'tags': instance.tags,
      'cover_individual_id': instance.coverIndividualId,
    };

AddMembersRequest _$AddMembersRequestFromJson(Map<String, dynamic> json) =>
    AddMembersRequest(
      individualIds: (json['individual_ids'] as List<dynamic>)
          .map((e) => e as String)
          .toList(),
      addedBy: json['added_by'] as String,
      notes: json['notes'] as String?,
    );

Map<String, dynamic> _$AddMembersRequestToJson(AddMembersRequest instance) =>
    <String, dynamic>{
      'individual_ids': instance.individualIds,
      'added_by': instance.addedBy,
      'notes': instance.notes,
    };

AddMembersResponse _$AddMembersResponseFromJson(Map<String, dynamic> json) =>
    AddMembersResponse(
      group: IndividualGroup.fromJson(json['group'] as Map<String, dynamic>),
      addedCount: (json['added_count'] as num).toInt(),
      skippedCount: (json['skipped_count'] as num).toInt(),
    );

Map<String, dynamic> _$AddMembersResponseToJson(AddMembersResponse instance) =>
    <String, dynamic>{
      'group': instance.group,
      'added_count': instance.addedCount,
      'skipped_count': instance.skippedCount,
    };

RemoveMembersRequest _$RemoveMembersRequestFromJson(
        Map<String, dynamic> json) =>
    RemoveMembersRequest(
      individualIds: (json['individual_ids'] as List<dynamic>)
          .map((e) => e as String)
          .toList(),
    );

Map<String, dynamic> _$RemoveMembersRequestToJson(
        RemoveMembersRequest instance) =>
    <String, dynamic>{
      'individual_ids': instance.individualIds,
    };

RemoveMembersResponse _$RemoveMembersResponseFromJson(
        Map<String, dynamic> json) =>
    RemoveMembersResponse(
      group: IndividualGroup.fromJson(json['group'] as Map<String, dynamic>),
      removedCount: (json['removed_count'] as num).toInt(),
    );

Map<String, dynamic> _$RemoveMembersResponseToJson(
        RemoveMembersResponse instance) =>
    <String, dynamic>{
      'group': instance.group,
      'removed_count': instance.removedCount,
    };

DuplicateMatch _$DuplicateMatchFromJson(Map<String, dynamic> json) =>
    DuplicateMatch(
      memberId: json['existing_member_id'] as String,
      memberName: json['existing_member_name'] as String?,
      similarity: (json['similarity_score'] as num).toDouble(),
      confidence: json['confidence'] as String,
      thumbnailUrl: json['thumbnail_url'] as String?,
    );

Map<String, dynamic> _$DuplicateMatchToJson(DuplicateMatch instance) =>
    <String, dynamic>{
      'existing_member_id': instance.memberId,
      'existing_member_name': instance.memberName,
      'similarity_score': instance.similarity,
      'confidence': instance.confidence,
      'thumbnail_url': instance.thumbnailUrl,
    };

CheckDuplicatesRequest _$CheckDuplicatesRequestFromJson(
        Map<String, dynamic> json) =>
    CheckDuplicatesRequest(
      candidateMvrUuid: json['candidate_mvr_uuid'] as String,
      similarityThreshold: (json['similarity_threshold'] as num?)?.toDouble(),
    );

Map<String, dynamic> _$CheckDuplicatesRequestToJson(
        CheckDuplicatesRequest instance) =>
    <String, dynamic>{
      'candidate_mvr_uuid': instance.candidateMvrUuid,
      'similarity_threshold': instance.similarityThreshold,
    };

CheckDuplicatesResponse _$CheckDuplicatesResponseFromJson(
        Map<String, dynamic> json) =>
    CheckDuplicatesResponse(
      hasDuplicates: json['has_duplicates'] as bool,
      matches: (json['matches'] as List<dynamic>)
          .map((e) => DuplicateMatch.fromJson(e as Map<String, dynamic>))
          .toList(),
      groupId: json['group_id'] as String,
      groupName: json['group_name'] as String,
      candidateId: json['candidate_mvr_uuid'] as String,
    );

Map<String, dynamic> _$CheckDuplicatesResponseToJson(
        CheckDuplicatesResponse instance) =>
    <String, dynamic>{
      'has_duplicates': instance.hasDuplicates,
      'matches': instance.matches,
      'group_id': instance.groupId,
      'group_name': instance.groupName,
      'candidate_mvr_uuid': instance.candidateId,
    };

MergeMembersRequest _$MergeMembersRequestFromJson(Map<String, dynamic> json) =>
    MergeMembersRequest(
      sourceMvrUuid: json['source_mvr_uuid'] as String,
      targetMvrUuid: json['target_mvr_uuid'] as String,
      userConfirmed: json['user_confirmed'] as bool? ?? true,
    );

Map<String, dynamic> _$MergeMembersRequestToJson(
        MergeMembersRequest instance) =>
    <String, dynamic>{
      'source_mvr_uuid': instance.sourceMvrUuid,
      'target_mvr_uuid': instance.targetMvrUuid,
      'user_confirmed': instance.userConfirmed,
    };

MergeMembersResponse _$MergeMembersResponseFromJson(
        Map<String, dynamic> json) =>
    MergeMembersResponse(
      superIndividualUuid: json['super_individual_uuid'] as String,
      mergedCount: (json['merged_count'] as num).toInt(),
      groupMembershipUpdated: json['group_membership_updated'] as bool,
      groupId: json['group_id'] as String,
    );

Map<String, dynamic> _$MergeMembersResponseToJson(
        MergeMembersResponse instance) =>
    <String, dynamic>{
      'super_individual_uuid': instance.superIndividualUuid,
      'merged_count': instance.mergedCount,
      'group_membership_updated': instance.groupMembershipUpdated,
      'group_id': instance.groupId,
    };
