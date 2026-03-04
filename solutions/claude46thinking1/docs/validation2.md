uv run python -c "
from pcontext import oneshot_script, File, Image, Video, Param, Extensions

# Проверяем объединение типов

combined = Image() | Video()
print(f'Combined: {combined}')
print(f'Extensions: {combined.extensions}')

# Проверяем Extensions

custom = Extensions(['jpg', 'png'])
print(f'Custom: {custom}')

# Проверяем Param

p = Param(0.5, ge=0.0, le=1.0, description='Порог')
print(f'Param: {p}')

# Проверяем декоратор

@oneshot_script(title='Test', timeout=10)
def test_fn(path: str = File(), threshold: float = Param(0.5)):
pass

meta = test_fn.**pcontext_meta**
print(f'Script: {meta.title}, inputs={len(meta.file_inputs)}, params={len(meta.params)}')
print('Всё работает!')
"
