/// Individual Groups Models
/// Data models for individual groups feature matching backend API
library;

import 'package:json_annotation/json_annotation.dart';

part 'individual_group_models.g.dart';

/// Visibility level for groups
enum GroupVisibility {
  @JsonValue('private')
  private,
  @JsonValue('shared')
  shared,
  @JsonValue('public')
  public,
}

/// Individual Group model
@JsonSerializable()
class IndividualGroup {
  final String id;
  final String name;
  final String? description;
  @JsonKey(name: 'created_by')
  final String createdBy;
  @JsonKey(name: 'created_at')
  final DateTime createdAt;
  @JsonKey(name: 'updated_at')
  final DateTime updatedAt;
  @JsonKey(name: 'member_count')
  final int memberCount;
  @JsonKey(name: 'member_ids')
  final List<String> memberIds;
  final GroupVisibility visibility;
  final List<String> tags;
  @JsonKey(name: 'cover_individual_id')
  final String? coverIndividualId;
  final Map<String, dynamic>? metadata;

  IndividualGroup({
    required this.id,
    required this.name,
    this.description,
    required this.createdBy,
    required this.createdAt,
    required this.updatedAt,
    required this.memberCount,
    required this.memberIds,
    required this.visibility,
    required this.tags,
    this.coverIndividualId,
    this.metadata,
  });

  factory IndividualGroup.fromJson(Map<String, dynamic> json) =>
      _$IndividualGroupFromJson(json);

  Map<String, dynamic> toJson() => _$IndividualGroupToJson(this);
}

/// Individual summary for group members
@JsonSerializable()
class IndividualSummary {
  final String id;
  @JsonKey(name: 'mvr_person_uuid')
  final String? mvrPersonUuid;
  @JsonKey(name: 'group_member_number')
  final int? groupMemberNumber;
  @JsonKey(name: 'thumbnail_url')
  final String? thumbnailUrl;
  @JsonKey(name: 'total_appearances')
  final int totalAppearances;
  @JsonKey(name: 'last_seen')
  final DateTime? lastSeen;
  @JsonKey(name: 'group_count')
  final int groupCount;
  @JsonKey(name: 'confidence_score')
  final double confidenceScore;
  
  // Individual naming (v2.21.0)
  final String? name;
  @JsonKey(name: 'name_updated_at')
  final DateTime? nameUpdatedAt;
  @JsonKey(name: 'name_updated_by')
  final String? nameUpdatedBy;

  IndividualSummary({
    required this.id,
    this.mvrPersonUuid,
    this.groupMemberNumber,
    this.thumbnailUrl,
    required this.totalAppearances,
    this.lastSeen,
    required this.groupCount,
    required this.confidenceScore,
    this.name,
    this.nameUpdatedAt,
    this.nameUpdatedBy,
  });

  factory IndividualSummary.fromJson(Map<String, dynamic> json) =>
      _$IndividualSummaryFromJson(json);

  Map<String, dynamic> toJson() => _$IndividualSummaryToJson(this);
}

/// List groups response
@JsonSerializable()
class ListGroupsResponse {
  final List<IndividualGroup> groups;
  final int total;
  final int skip;
  final int limit;

  ListGroupsResponse({
    required this.groups,
    required this.total,
    required this.skip,
    required this.limit,
  });

  factory ListGroupsResponse.fromJson(Map<String, dynamic> json) =>
      _$ListGroupsResponseFromJson(json);

  Map<String, dynamic> toJson() => _$ListGroupsResponseToJson(this);
}

/// Get group response with members preview
@JsonSerializable()
class GetGroupResponse {
  final IndividualGroup group;
  @JsonKey(name: 'members_preview')
  final List<IndividualSummary> membersPreview;

  GetGroupResponse({
    required this.group,
    required this.membersPreview,
  });

  factory GetGroupResponse.fromJson(Map<String, dynamic> json) =>
      _$GetGroupResponseFromJson(json);

  Map<String, dynamic> toJson() => _$GetGroupResponseToJson(this);
}

/// List group members response
@JsonSerializable()
class ListMembersResponse {
  final List<IndividualSummary> members;
  final int total;
  final int skip;
  final int limit;

  ListMembersResponse({
    required this.members,
    required this.total,
    required this.skip,
    required this.limit,
  });

  factory ListMembersResponse.fromJson(Map<String, dynamic> json) =>
      _$ListMembersResponseFromJson(json);

  Map<String, dynamic> toJson() => _$ListMembersResponseToJson(this);
}

/// Create group request
@JsonSerializable()
class CreateGroupRequest {
  final String name;
  final String? description;
  final GroupVisibility visibility;
  final List<String> tags;
  @JsonKey(name: 'initial_member_ids')
  final List<String> initialMemberIds;

  CreateGroupRequest({
    required this.name,
    this.description,
    this.visibility = GroupVisibility.private,
    this.tags = const [],
    this.initialMemberIds = const [],
  });

  factory CreateGroupRequest.fromJson(Map<String, dynamic> json) =>
      _$CreateGroupRequestFromJson(json);

  Map<String, dynamic> toJson() => _$CreateGroupRequestToJson(this);
}

/// Update group request
@JsonSerializable()
class UpdateGroupRequest {
  final String? name;
  final String? description;
  final GroupVisibility? visibility;
  final List<String>? tags;
  @JsonKey(name: 'cover_individual_id')
  final String? coverIndividualId;

  UpdateGroupRequest({
    this.name,
    this.description,
    this.visibility,
    this.tags,
    this.coverIndividualId,
  });

  factory UpdateGroupRequest.fromJson(Map<String, dynamic> json) =>
      _$UpdateGroupRequestFromJson(json);

  Map<String, dynamic> toJson() => _$UpdateGroupRequestToJson(this);
}

/// Add members request
@JsonSerializable()
class AddMembersRequest {
  @JsonKey(name: 'individual_ids')
  final List<String> individualIds;
  @JsonKey(name: 'added_by')
  final String addedBy;
  final String? notes;

  AddMembersRequest({
    required this.individualIds,
    required this.addedBy,
    this.notes,
  });

  factory AddMembersRequest.fromJson(Map<String, dynamic> json) =>
      _$AddMembersRequestFromJson(json);

  Map<String, dynamic> toJson() => _$AddMembersRequestToJson(this);
}

/// Add members response
@JsonSerializable()
class AddMembersResponse {
  final IndividualGroup group;
  @JsonKey(name: 'added_count')
  final int addedCount;
  @JsonKey(name: 'skipped_count')
  final int skippedCount;

  AddMembersResponse({
    required this.group,
    required this.addedCount,
    required this.skippedCount,
  });

  factory AddMembersResponse.fromJson(Map<String, dynamic> json) =>
      _$AddMembersResponseFromJson(json);

  Map<String, dynamic> toJson() => _$AddMembersResponseToJson(this);
}

/// Remove members request
@JsonSerializable()
class RemoveMembersRequest {
  @JsonKey(name: 'individual_ids')
  final List<String> individualIds;

  RemoveMembersRequest({
    required this.individualIds,
  });

  factory RemoveMembersRequest.fromJson(Map<String, dynamic> json) =>
      _$RemoveMembersRequestFromJson(json);

  Map<String, dynamic> toJson() => _$RemoveMembersRequestToJson(this);
}

/// Remove members response
@JsonSerializable()
class RemoveMembersResponse {
  final IndividualGroup group;
  @JsonKey(name: 'removed_count')
  final int removedCount;

  RemoveMembersResponse({
    required this.group,
    required this.removedCount,
  });

  factory RemoveMembersResponse.fromJson(Map<String, dynamic> json) =>
      _$RemoveMembersResponseFromJson(json);

  Map<String, dynamic> toJson() => _$RemoveMembersResponseToJson(this);
}

/// Duplicate match model
@JsonSerializable()
class DuplicateMatch {
  @JsonKey(name: 'existing_member_id')
  final String memberId;
  @JsonKey(name: 'existing_member_name')
  final String? memberName;
  @JsonKey(name: 'similarity_score')
  final double similarity;
  final String confidence;
  @JsonKey(name: 'thumbnail_url')
  final String? thumbnailUrl;

  DuplicateMatch({
    required this.memberId,
    this.memberName,
    required this.similarity,
    required this.confidence,
    this.thumbnailUrl,
  });

  factory DuplicateMatch.fromJson(Map<String, dynamic> json) =>
      _$DuplicateMatchFromJson(json);

  Map<String, dynamic> toJson() => _$DuplicateMatchToJson(this);
}

/// Check duplicates request
@JsonSerializable()
class CheckDuplicatesRequest {
  @JsonKey(name: 'candidate_mvr_uuid')
  final String candidateMvrUuid;
  @JsonKey(name: 'similarity_threshold')
  final double? similarityThreshold;

  CheckDuplicatesRequest({
    required this.candidateMvrUuid,
    this.similarityThreshold,
  });

  factory CheckDuplicatesRequest.fromJson(Map<String, dynamic> json) =>
      _$CheckDuplicatesRequestFromJson(json);

  Map<String, dynamic> toJson() => _$CheckDuplicatesRequestToJson(this);
}

/// Check duplicates response
@JsonSerializable()
class CheckDuplicatesResponse {
  @JsonKey(name: 'has_duplicates')
  final bool hasDuplicates;
  final List<DuplicateMatch> matches;
  @JsonKey(name: 'group_id')
  final String groupId;
  @JsonKey(name: 'group_name')
  final String groupName;
  @JsonKey(name: 'candidate_mvr_uuid')
  final String candidateId;

  CheckDuplicatesResponse({
    required this.hasDuplicates,
    required this.matches,
    required this.groupId,
    required this.groupName,
    required this.candidateId,
  });

  factory CheckDuplicatesResponse.fromJson(Map<String, dynamic> json) =>
      _$CheckDuplicatesResponseFromJson(json);

  Map<String, dynamic> toJson() => _$CheckDuplicatesResponseToJson(this);
}

/// Merge members request
@JsonSerializable()
class MergeMembersRequest {
  @JsonKey(name: 'source_mvr_uuid')
  final String sourceMvrUuid;
  @JsonKey(name: 'target_mvr_uuid')
  final String targetMvrUuid;
  @JsonKey(name: 'user_confirmed')
  final bool userConfirmed;

  MergeMembersRequest({
    required this.sourceMvrUuid,
    required this.targetMvrUuid,
    this.userConfirmed = true,
  });

  factory MergeMembersRequest.fromJson(Map<String, dynamic> json) =>
      _$MergeMembersRequestFromJson(json);

  Map<String, dynamic> toJson() => _$MergeMembersRequestToJson(this);
}

/// Merge members response
@JsonSerializable()
class MergeMembersResponse {
  @JsonKey(name: 'super_individual_uuid')
  final String superIndividualUuid;
  @JsonKey(name: 'merged_count')
  final int mergedCount;
  @JsonKey(name: 'group_membership_updated')
  final bool groupMembershipUpdated;
  @JsonKey(name: 'group_id')
  final String groupId;

  MergeMembersResponse({
    required this.superIndividualUuid,
    required this.mergedCount,
    required this.groupMembershipUpdated,
    required this.groupId,
  });

  factory MergeMembersResponse.fromJson(Map<String, dynamic> json) =>
      _$MergeMembersResponseFromJson(json);

  Map<String, dynamic> toJson() => _$MergeMembersResponseToJson(this);
}
