<?php
/**
 * Страница точки. Подставляется, только если тема не предложила свою
 * single-geo_point.php — переопределить можно, скопировав файл в тему.
 */

defined('ABSPATH') || exit;

get_header();

$gp_point = GeoPoints\Point::data(get_queried_object_id());

while (have_posts()) :
	the_post();
	?>
	<main id="primary" class="gp-page">
		<article <?php post_class('gp-point'); ?>>
			<header class="gp-point__head">
				<h1 class="gp-point__title"><?php the_title(); ?></h1>
				<?php if (!empty($gp_point['intro'])) : ?>
					<p class="gp-point__lead"><?php echo esc_html($gp_point['intro']); ?></p>
				<?php endif; ?>
			</header>

			<?php
			echo GeoPoints\Render::nap($gp_point);
			echo GeoPoints\Render::map($gp_point);
			?>

			<div class="gp-content">
				<?php the_content(); ?>
			</div>

			<?php if (!empty($gp_point['streets'])) : ?>
				<section class="gp-served">
					<h2>Куда выезжаем из этой мастерской</h2>
					<p><?php echo esc_html(implode(', ', $gp_point['streets'])); ?>.</p>
				</section>
			<?php endif; ?>

			<?php
			echo GeoPoints\Render::reviews($gp_point);
			echo GeoPoints\Render::cta($gp_point);
			echo GeoPoints\Render::others($gp_point);
			?>
		</article>
	</main>
	<?php
endwhile;

get_footer();
