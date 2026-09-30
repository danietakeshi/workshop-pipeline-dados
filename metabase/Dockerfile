# A imagem oficial metabase/metabase:latest é baseada em Alpine (musl libc).
# O driver nativo do DuckDB é compilado para glibc e trava a JVM com SIGSEGV
# em malloc_init_hard quando carregado em Alpine (bug conhecido, não é algo
# que dê pra contornar instalando libstdc++/gcompat — testado e confirmado
# neste projeto). A solução da própria comunidade DuckDB/Metabase é rodar o
# Metabase sobre uma base Debian/Ubuntu com glibc de verdade.

FROM eclipse-temurin:25-jre

ENV MB_PLUGINS_DIR=/plugins
RUN mkdir -p ${MB_PLUGINS_DIR} /app

ADD https://downloads.metabase.com/latest/metabase.jar /app/metabase.jar
ADD https://github.com/motherduckdb/metabase_duckdb_driver/releases/download/1.5.5.0/duckdb.metabase-driver.jar ${MB_PLUGINS_DIR}/duckdb.metabase-driver.jar

EXPOSE 3000
CMD ["java", "-jar", "/app/metabase.jar"]
