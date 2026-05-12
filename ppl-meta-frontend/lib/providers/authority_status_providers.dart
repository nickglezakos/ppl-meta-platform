import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../services/authority_status_client.dart';

final authorityStatusProvider = FutureProvider<AuthorityStatus>((ref) async {
  final client = ref.watch(authorityStatusClientProvider);
  return client.getAuthorityStatus();
});