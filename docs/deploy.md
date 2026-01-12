# Deploy notes

## Static cache headers (nginx example)

```
location /static/ {
    alias /var/www/pasue/static/;
    access_log off;
    expires 1y;
    add_header Cache-Control "public, max-age=31536000, immutable" always;
}
```

## Django static workflow

1. Collect static files:

```
python manage.py collectstatic
```

2. Purge CDN/cache after deploy to ensure new CSS/HTML is served.
