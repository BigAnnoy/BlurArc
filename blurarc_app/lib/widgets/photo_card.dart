import 'package:flutter/material.dart';
import 'package:cached_network_image/cached_network_image.dart';
import '../models/photo.dart';
import '../services/api_client.dart';

class PhotoCard extends StatelessWidget {
  final Photo photo;
  final ApiClient api;
  final VoidCallback onTap;

  const PhotoCard({
    super.key,
    required this.photo,
    required this.api,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: ClipRRect(
        borderRadius: BorderRadius.circular(4),
        child: Stack(
          fit: StackFit.expand,
          children: [
            CachedNetworkImage(
              imageUrl: api.getThumbnailUrl(photo.path),
              fit: BoxFit.cover,
              placeholder: (_, __) => Container(
                color: Colors.grey[800],
                child: const Center(
                    child: Icon(Icons.photo, color: Colors.grey, size: 32)),
              ),
              errorWidget: (_, __, ___) => Container(
                color: Colors.grey[800],
                child: const Center(
                    child: Icon(Icons.broken_image, color: Colors.grey)),
              ),
            ),
            if (photo.isVideo)
              const Center(
                child: Icon(Icons.play_circle_fill,
                    color: Colors.white54, size: 36),
              ),
            Positioned(
              bottom: 2,
              right: 4,
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 1),
                decoration: BoxDecoration(
                  color: Colors.black54,
                  borderRadius: BorderRadius.circular(3),
                ),
                child: Text(
                  photo.name,
                  style: const TextStyle(fontSize: 9, color: Colors.white70),
                  overflow: TextOverflow.ellipsis,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
